#!/bin/bash
# range_migrate.sh - Simple range-based migration script
# 
# Migrates Jira issues in sequential ranges (e.g., PROJ-1 to PROJ-50, then PROJ-51 to PROJ-100)
#
# Usage: ./range_migrate.sh PROJECT START_NUM END_NUM BATCH_SIZE [DELAY_MINUTES]
# Example: ./range_migrate.sh PROJ 1 500 50 15
#   This migrates PROJ-1 through PROJ-500 in batches of 50, waiting 15 minutes between batches

set -e

# Configuration
PROJECT="$1"
START_NUM="$2" 
END_NUM="$3"
BATCH_SIZE="${4:-50}"
DELAY_MINUTES="${5:-10}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validate arguments
if [[ -z "$PROJECT" || -z "$START_NUM" || -z "$END_NUM" ]]; then
    echo -e "${RED}Usage: $0 PROJECT START_NUM END_NUM [BATCH_SIZE] [DELAY_MINUTES]${NC}"
    echo -e "${YELLOW}Example: $0 PROJ 1 500 50 15${NC}"
    echo ""
    echo "This will migrate:"
    echo "  - PROJ-1 to PROJ-50 (first batch)"
    echo "  - PROJ-51 to PROJ-100 (second batch)"  
    echo "  - ... and so on until PROJ-500"
    echo "  - With 15 minute delays between batches"
    exit 1
fi

# Check for user mapping file
MAPPING_FILE="user-mapping-${PROJECT,,}.json"
if [[ -f "$MAPPING_FILE" ]]; then
    FLAGS="--user-mapping-file=$MAPPING_FILE --auto-create-labels --migrate-closed-as-closed"
    echo -e "${GREEN}✅ Using user mapping file: $MAPPING_FILE${NC}"
else
    FLAGS="--auto-create-labels --migrate-closed-as-closed"
    echo -e "${YELLOW}⚠️  No user mapping file found. Continuing without user mapping.${NC}"
fi

echo -e "${BLUE}🚀 Range-based Migration Configuration${NC}"
echo "===================================="
echo "Project: $PROJECT"
echo "Range: $PROJECT-$START_NUM to $PROJECT-$END_NUM"
echo "Batch Size: $BATCH_SIZE issues per batch"
echo "Delay: $DELAY_MINUTES minutes between batches"
echo "Enhancement Flags: $FLAGS"
echo ""

# Calculate total issues and batches
TOTAL_ISSUES=$((END_NUM - START_NUM + 1))
TOTAL_BATCHES=$(((TOTAL_ISSUES + BATCH_SIZE - 1) / BATCH_SIZE))

echo -e "${BLUE}📊 Migration Plan${NC}"
echo "Total issues to migrate: $TOTAL_ISSUES"
echo "Number of batches: $TOTAL_BATCHES" 
echo ""

# Show first few batch ranges as examples
echo -e "${BLUE}Batch breakdown (first few examples):${NC}"
for ((batch=1; batch<=3 && batch<=TOTAL_BATCHES; batch++)); do
    batch_start=$((START_NUM + (batch - 1) * BATCH_SIZE))
    batch_end=$((batch_start + BATCH_SIZE - 1))
    
    # Don't exceed the end number
    if [[ $batch_end -gt $END_NUM ]]; then
        batch_end=$END_NUM
    fi
    
    echo "  Batch $batch: $PROJECT-$batch_start to $PROJECT-$batch_end"
done

if [[ $TOTAL_BATCHES -gt 3 ]]; then
    echo "  ... ($((TOTAL_BATCHES - 3)) more batches)"
fi
echo ""

# Confirm before starting
read -p "Continue with migration? (y/n) [y]: " confirm
confirm=${confirm:-y}

if [[ ! "$confirm" =~ ^[Yy] ]]; then
    echo -e "${YELLOW}Migration cancelled by user${NC}"
    exit 0
fi

echo -e "${GREEN}🚀 Starting range-based migration...${NC}"
echo ""

# Migration loop
successful_batches=0
failed_batches=0

for ((batch=1; batch<=TOTAL_BATCHES; batch++)); do
    # Calculate range for this batch
    batch_start=$((START_NUM + (batch - 1) * BATCH_SIZE))
    batch_end=$((batch_start + BATCH_SIZE - 1))
    
    # Don't exceed the end number
    if [[ $batch_end -gt $END_NUM ]]; then
        batch_end=$END_NUM
    fi
    
    echo -e "${BLUE}🔄 Starting batch $batch/$TOTAL_BATCHES${NC}"
    echo "Range: $PROJECT-$batch_start to $PROJECT-$batch_end"
    echo "Time: $(date)"
    
    # Generate issue keys for this batch
    issue_keys=()
    for ((i=batch_start; i<=batch_end; i++)); do
        issue_keys+=("$PROJECT-$i")
    done
    
    echo "Issues in this batch: ${issue_keys[*]}"
    
    # Run migration for this batch
    if ./run.sh $FLAGS migrate "${issue_keys[@]}"; then
        echo -e "${GREEN}✅ Batch $batch completed successfully${NC}"
        ((successful_batches++))
    else
        echo -e "${RED}❌ Batch $batch failed${NC}"
        ((failed_batches++))
        
        # Ask user what to do
        echo ""
        echo "Options:"
        echo "  c) Continue with next batch"
        echo "  r) Retry this batch" 
        echo "  q) Quit migration"
        
        read -p "What would you like to do? (c/r/q) [c]: " choice
        choice=${choice:-c}
        
        case $choice in
            r|R)
                echo "Retrying batch $batch..."
                if ./run.sh $FLAGS migrate "${issue_keys[@]}"; then
                    echo -e "${GREEN}✅ Batch $batch retry successful${NC}"
                    ((successful_batches++))
                    ((failed_batches--))  # Adjust count since retry succeeded
                else
                    echo -e "${RED}❌ Batch $batch retry also failed${NC}"
                fi
                ;;
            q|Q)
                echo -e "${YELLOW}🛑 Migration stopped by user${NC}"
                break
                ;;
            c|C|*)
                echo "Continuing to next batch..."
                ;;
        esac
    fi
    
    # Progress summary
    echo -e "${BLUE}Progress: $successful_batches successful, $failed_batches failed${NC}"
    
    # Delay between batches (except for the last one)
    if [[ $batch -lt $TOTAL_BATCHES ]]; then
        echo -e "${YELLOW}⏳ Waiting $DELAY_MINUTES minutes before next batch...${NC}"
        
        # Visual progress bar for the delay
        echo -n "Countdown: "
        for ((j=DELAY_MINUTES; j>=1; j--)); do
            printf "%2d" $j
            sleep 60
            if [[ $j -gt 1 ]]; then
                printf "\b\b"  # Backspace to overwrite
            fi
        done
        echo -e " ${GREEN}Ready!${NC}"
    fi
    
    echo ""
done

# Final summary
echo ""
echo -e "${GREEN}🎉 Range migration completed!${NC}"
echo "================================"
echo "Total batches: $TOTAL_BATCHES"
echo -e "Successful: ${GREEN}$successful_batches${NC}"
echo -e "Failed: ${RED}$failed_batches${NC}"
echo "Range: $PROJECT-$START_NUM to $PROJECT-$END_NUM"

if [[ $failed_batches -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}💡 For failed batches, you can:${NC}"
    echo "  - Check GitHub repository for successfully migrated issues"
    echo "  - Re-run specific ranges that failed"
    echo "  - Check GitHub API rate limits: curl -H \"Authorization: token \$GITHUB_TOKEN\" https://api.github.com/rate_limit"
fi

echo ""
echo -e "${BLUE}🔍 Next steps:${NC}"
echo "  - Check your GitHub repository for the migrated issues"
echo "  - Run './run.sh info' to verify configuration"
echo "  - Consider running './run.sh test-connection' to check API status"