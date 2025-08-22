#!/bin/bash
# batch_migrate.sh - Smart batch migration script for Jira to GitHub
# 
# This script handles large migrations by breaking them into manageable batches
# to respect GitHub API rate limits and provide recovery options.
#
# Usage: ./batch_migrate.sh PROJ [batch_size] [delay_minutes]
# Example: ./batch_migrate.sh MYPROJECT 50 10

# Check bash version compatibility
if [[ ${BASH_VERSION%%.*} -lt 3 ]]; then
    echo "Error: This script requires Bash 3.0 or higher. Current version: $BASH_VERSION"
    exit 1
fi

set -e  # Exit on any error

# Configuration
PROJECT="${1:-PROJ}"
BATCH_SIZE="${2:-50}"
DELAY_MINUTES="${3:-10}"
TOTAL_COUNT_OVERRIDE="${4:-}"  # Optional: manually specify total count
MAPPING_FILE="user-mapping-$(echo "$PROJECT" | tr '[:upper:]' '[:lower:]').json"  # Convert to lowercase

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced migration flags
FLAGS="--user-mapping-file=$MAPPING_FILE --auto-create-labels --migrate-closed-as-closed"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check if run script exists
    if [[ ! -f "./run.sh" ]]; then
        log_error "run.sh not found. Make sure you're in the project directory."
        exit 1
    fi
    
    # Check if user mapping file exists
    if [[ -f "$MAPPING_FILE" ]]; then
        log_success "User mapping file found: $MAPPING_FILE"
        
        # Validate mapping file
        local validation_output=$(./run.sh validate-user-mapping "$MAPPING_FILE" 2>&1)
        if [[ $? -eq 0 ]]; then
            log_success "User mapping file is valid"
        else
            log_warning "User mapping file has issues: $(echo "$validation_output" | head -1)"
            log_warning "Migration will continue without user mapping"
            FLAGS="--auto-create-labels --migrate-closed-as-closed"  # Remove user mapping flag
        fi
    else
        log_warning "No user mapping file found at $MAPPING_FILE"
        log_info "Consider running: ./run.sh generate-user-mapping $PROJECT"
        FLAGS="--auto-create-labels --migrate-closed-as-closed"  # Remove user mapping flag
    fi
    
    # Test connection
    log_step "Testing connections..."
    local connection_output=$(./run.sh test-connection 2>&1)
    if [[ $? -eq 0 ]]; then
        log_success "Jira and GitHub connections are working"
    else
        log_error "Connection test failed:"
        echo "$connection_output"
        log_error "Check your .env configuration."
        exit 1
    fi
}

get_issue_count() {
    local jql="$1"
    
    # If user provided a total count override, use it
    if [[ -n "$TOTAL_COUNT_OVERRIDE" ]]; then
        log_info "Using manual count override: $TOTAL_COUNT_OVERRIDE" >&2
        echo "$TOTAL_COUNT_OVERRIDE"
        return
    fi
    
    log_step "Counting issues for: $jql" >&2
    
    # Use dry-run to count issues without creating them
    local output=$(./run.sh --dry-run migrate-jql "$jql" --max-results 1 2>&1)
    local count=$(echo "$output" | grep -o "Found [0-9]* issues" | grep -o "[0-9]*" | head -1)
    
    # Check for unbounded query error
    if echo "$output" | grep -q "Unbounded JQL queries are not allowed"; then
        log_warning "Cannot count issues due to JQL restrictions. Using estimate." >&2
        count="1000"  # Use conservative estimate
    fi
    
    if [[ -z "$count" ]]; then
        count=0
    fi
    
    echo "$count"
}

migrate_batch() {
    local jql="$1"
    local batch_num="$2"
    local max_results="$3"
    
    log_step "Executing batch $batch_num: $jql"
    log_info "Max results: $max_results"
    log_info "$(date)"
    
    # Run the actual migration
    ./run.sh $FLAGS migrate-jql "$jql" --max-results "$max_results"
    
    return $?
}

check_rate_limit() {
    # Check GitHub rate limit if token is available
    if [[ -n "$GITHUB_TOKEN" ]]; then
        local remaining=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit 2>/dev/null | jq -r '.rate.remaining' 2>/dev/null)
        
        if [[ "$remaining" != "null" && "$remaining" -gt 0 ]]; then
            log_info "GitHub API requests remaining: $remaining"
            
            if [[ "$remaining" -lt 100 ]]; then
                log_warning "Low API rate limit remaining. Consider waiting longer between batches."
            fi
        fi
    fi
}

show_config() {
    echo -e "${CYAN}📋 Batch Migration Configuration${NC}"
    echo "================================"
    echo "Project: $PROJECT"
    echo "Batch Size: $BATCH_SIZE issues"
    echo "Delay: $DELAY_MINUTES minutes"
    echo "Mapping File: $MAPPING_FILE"
    echo "Flags: $FLAGS"
    echo ""
}

main() {
    # Show banner
    echo -e "${CYAN}"
    echo "🚀 Jira to GitHub Batch Migration Script"
    echo "========================================"
    echo -e "${NC}"
    
    # Validate arguments
    if [[ -z "$PROJECT" ]]; then
        log_error "Usage: $0 PROJECT [batch_size] [delay_minutes] [total_count]"
        log_error "Example: $0 MYPROJECT 50 10"
        log_error "Example with manual count: $0 MYPROJECT 50 10 500"
        exit 1
    fi
    
    show_config
    check_prerequisites
    
    # Ask user for migration strategy
    echo -e "${YELLOW}Select migration strategy:${NC}"
    echo "1. Migrate all issues (default)"
    echo "2. Migrate by status (closed first, then open)"  
    echo "3. Migrate by priority (high first, then medium, then low)"
    echo "4. Migrate by date range (you'll be prompted for dates)"
    echo "5. Custom JQL query (you'll be prompted)"
    
    read -p "Choose strategy (1-5) [1]: " strategy
    strategy=${strategy:-1}
    
    case $strategy in
        1)
            # All issues
            JQL_QUERIES=("project = $PROJECT ORDER BY key ASC")
            BATCH_NAMES=("All Issues")
            ;;
        2) 
            # By status
            JQL_QUERIES=(
                "project = $PROJECT AND status in (Done, Closed, Resolved, 'Won\'t Fix', Duplicate) ORDER BY key ASC"
                "project = $PROJECT AND status in ('In Progress', 'Code Review', Testing) ORDER BY key ASC" 
                "project = $PROJECT AND status in (Open, 'To Do', Backlog, New) ORDER BY key ASC"
            )
            BATCH_NAMES=("Closed Issues" "In-Progress Issues" "Open Issues")
            ;;
        3)
            # By priority
            JQL_QUERIES=(
                "project = $PROJECT AND priority in (Blocker, Critical, High) ORDER BY key ASC"
                "project = $PROJECT AND priority = Medium ORDER BY key ASC"
                "project = $PROJECT AND priority in (Low, Trivial) ORDER BY key ASC"
            )
            BATCH_NAMES=("High Priority" "Medium Priority" "Low Priority") 
            ;;
        4)
            # By date range
            echo -e "${YELLOW}Enter date ranges (format: YYYY-MM-DD):${NC}"
            read -p "Start date: " start_date
            read -p "End date: " end_date
            
            JQL_QUERIES=("project = $PROJECT AND created >= '$start_date' AND created <= '$end_date' ORDER BY key ASC")
            BATCH_NAMES=("Date Range: $start_date to $end_date")
            ;;
        5)
            # Custom JQL
            echo -e "${YELLOW}Enter custom JQL query:${NC}"
            echo "Note: 'project = $PROJECT' will be prepended automatically"
            read -p "Additional JQL: " custom_jql
            
            if [[ -n "$custom_jql" ]]; then
                JQL_QUERIES=("project = $PROJECT AND ($custom_jql) ORDER BY key ASC")
            else
                JQL_QUERIES=("project = $PROJECT ORDER BY key ASC")
            fi
            BATCH_NAMES=("Custom Query")
            ;;
        *)
            log_error "Invalid strategy selected"
            exit 1
            ;;
    esac
    
    # Process each JQL query
    for i in "${!JQL_QUERIES[@]}"; do
        jql="${JQL_QUERIES[$i]}"
        batch_name="${BATCH_NAMES[$i]}"
        
        echo ""
        log_step "Processing: $batch_name"
        log_info "JQL: $jql"
        
        # Get total count for this query
        total_count=$(get_issue_count "$jql")
        
        if [[ "$total_count" -eq 0 ]]; then
            log_warning "No issues found for: $batch_name"
            continue
        fi
        
        log_success "Found $total_count issues for: $batch_name"
        
        # Calculate number of batches needed
        total_batches=$(((total_count + BATCH_SIZE - 1) / BATCH_SIZE))
        log_info "Will process in $total_batches batches of $BATCH_SIZE issues each"
        
        # Confirm before proceeding
        read -p "Proceed with $batch_name migration? (y/n) [y]: " confirm
        confirm=${confirm:-y}
        
        if [[ ! "$confirm" =~ ^[Yy] ]]; then
            log_warning "Skipping: $batch_name"
            continue
        fi
        
        # Process batches for this query
        batch_success=0
        batch_failed=0
        
        for ((batch=1; batch<=total_batches; batch++)); do
            echo ""
            log_step "Batch $batch/$total_batches for: $batch_name"
            
            # Check rate limit
            check_rate_limit
            
            if migrate_batch "$jql" "$batch" "$BATCH_SIZE"; then
                log_success "Batch $batch/$total_batches completed successfully"
                ((batch_success++))
            else
                log_error "Batch $batch/$total_batches failed"
                ((batch_failed++))
                
                read -p "Continue with next batch? (y/n/q) [y]: " continue_choice
                continue_choice=${continue_choice:-y}
                
                case $continue_choice in
                    q|Q)
                        log_warning "Migration stopped by user"
                        exit 1
                        ;;
                    n|N)
                        log_warning "Skipping remaining batches for: $batch_name"
                        break
                        ;;
                esac
            fi
            
            # Delay between batches (except for the last one)
            if [[ $batch -lt $total_batches ]]; then
                log_info "Waiting $DELAY_MINUTES minutes before next batch..."
                echo -n "Progress: "
                for ((j=1; j<=DELAY_MINUTES; j++)); do
                    sleep 60
                    echo -n "█"
                done
                echo " Done!"
            fi
        done
        
        log_success "$batch_name completed: $batch_success successful, $batch_failed failed"
    done
    
    echo ""
    log_success "🎉 Batch migration completed!"
    log_info "📊 Check GitHub repository for migrated issues"
    log_info "🔍 Run './run.sh info' for configuration summary"
    
    # Show final rate limit status
    check_rate_limit
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}🛑 Migration interrupted by user${NC}"; exit 130' INT

# Run main function
main "$@"