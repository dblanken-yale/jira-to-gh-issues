# Enhanced Jira to GitHub Migration Workflow

This document demonstrates the complete enhanced migration workflow with user mapping, label enhancement, and closed issue migration.

## Step 1: Generate User Mapping Template

First, discover all users associated with your Jira project and generate a mapping template:

```bash
# Generate user mapping for project PROJ
./run.sh generate-user-mapping PROJ

# Or specify custom output file
./run.sh generate-user-mapping PROJ --output-file my-users.json
```

This creates a file like `user-mapping-proj.json` with all discovered users:

```json
{
  "_metadata": {
    "project": "PROJ",
    "generated": "2024-01-15T10:30:00",
    "total_users": 47,
    "sources_used": ["assignable", "issue_history", "role_member"]
  },
  "user_mapping": {
    "john.doe@company.com": {
      "display_name": "John Doe",
      "jira_account_id": "abc123",
      "roles": ["Developers"],
      "issue_activity_count": 89,
      "github_username": null,  // ← Fill this in!
      "notes": ""
    }
  }
}
```

## Step 2: Fill in GitHub Usernames

Edit the generated file and add GitHub usernames for users you want to map:

```json
{
  "user_mapping": {
    "john.doe@company.com": {
      "display_name": "John Doe",
      "github_username": "johndoe-dev",  // ← Added!
      "notes": "Lead developer"
    },
    "jane.smith@company.com": {
      "github_username": "jsmith",       // ← Added!
      "notes": "Project manager"
    }
  }
}
```

## Step 3: Validate Your Mapping

Check that your mapping file is valid:

```bash
# Validate the mapping
./run.sh validate-user-mapping user-mapping-proj.json

# Show detailed statistics
./run.sh show-mapping-stats user-mapping-proj.json
```

Output:
```
✅ Mapping file is valid with 23 mapped users

        User Mapping Statistics        
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric         ┃ Value               ┃
┃ Total Users    ┃ 47                  ┃
┃ Mapped Users   ┃ 23                  ┃
┃ Completion     ┃ 48.9%               ┃
└────────────────┴─────────────────────┘
```

## Step 4: Enhanced Migration

Now run migrations with all enhancements enabled:

### Basic Enhanced Migration

```bash
# Migrate with user mapping only
./run.sh --user-mapping-file=user-mapping-proj.json migrate PROJ-123 PROJ-124

# With auto-label creation
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate PROJ-123

# With closed issue migration
./run.sh --user-mapping-file=user-mapping-proj.json --migrate-closed-as-closed migrate PROJ-123

# All enhancements enabled
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate PROJ-123
```

## 🚀 Batch Migration Strategy

### Understanding GitHub Limits

GitHub has API rate limits that can affect large migrations:
- **Authenticated requests**: 5,000 per hour (personal token)
- **GitHub Apps**: 15,000 per hour  
- **Issue creation**: ~1-3 API calls per issue (depending on comments/labels)
- **Label creation**: 1 API call per new label

### Recommended Batch Sizes

**Conservative approach** (recommended for first-time users):
- **25-50 issues per batch** for comprehensive migrations with comments
- **50-100 issues per batch** for simple migrations without comments
- **Wait 10-15 minutes between large batches** to avoid rate limits

### Sequential Range Migration

#### Method 1: Issue Key Ranges

```bash
# Batch 1: PROJ-1 to PROJ-50
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate PROJ-1 PROJ-2 PROJ-3 ... PROJ-50

# More practical: Generate ranges
for i in {1..50}; do echo "PROJ-$i"; done | xargs ./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate

# Batch 2: PROJ-51 to PROJ-100  
for i in {51..100}; do echo "PROJ-$i"; done | xargs ./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate

# Batch 3: PROJ-101 to PROJ-150
for i in {101..150}; do echo "PROJ-$i"; done | xargs ./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate
```

#### Method 2: JQL-Based Batching (Recommended)

Use JQL queries to create natural batches:

```bash
# Batch by creation date ranges
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ AND created >= '2023-01-01' AND created <= '2023-03-31'"

./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ AND created >= '2023-04-01' AND created <= '2023-06-30'"

# Batch by issue type
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ AND type = Bug" --max-results 50

./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ AND type = Story" --max-results 50

# Batch by status (migrate closed issues first)
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate-jql "project = PROJ AND status in (Done, Closed, Resolved)" --max-results 100

./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ AND status in (Open, 'In Progress', 'To Do')" --max-results 100
```

#### Method 3: Smart Batching Script

Create a batching script for complex scenarios:

```bash
#!/bin/bash
# batch_migrate.sh - Smart batch migration script

PROJECT="PROJ"
MAPPING_FILE="user-mapping-proj.json"
BATCH_SIZE=50
DELAY_MINUTES=10

# Enhanced migration flags
FLAGS="--user-mapping-file=$MAPPING_FILE --auto-create-labels --migrate-closed-as-closed"

echo "🚀 Starting batch migration for project $PROJECT"
echo "📊 Batch size: $BATCH_SIZE issues"
echo "⏱️  Delay between batches: $DELAY_MINUTES minutes"

# Get total issue count first
echo "🔍 Counting total issues..."
TOTAL_ISSUES=$(./run.sh migrate-jql "project = $PROJECT" --max-results 1000 --dry-run 2>/dev/null | grep -o "Found [0-9]* issues" | grep -o "[0-9]*")

echo "📋 Found $TOTAL_ISSUES total issues to migrate"
TOTAL_BATCHES=$(((TOTAL_ISSUES + BATCH_SIZE - 1) / BATCH_SIZE))
echo "📦 Will create $TOTAL_BATCHES batches"

# Migration loop
for ((batch=1; batch<=TOTAL_BATCHES; batch++)); do
    OFFSET=$((($batch - 1) * BATCH_SIZE))
    
    echo ""
    echo "🔄 Starting batch $batch/$TOTAL_BATCHES (offset: $OFFSET)"
    echo "⏰ $(date)"
    
    # Use JQL with ORDER BY key and LIMIT/OFFSET simulation
    ./run.sh $FLAGS migrate-jql "project = $PROJECT ORDER BY key ASC" --max-results $BATCH_SIZE
    
    if [ $? -eq 0 ]; then
        echo "✅ Batch $batch completed successfully"
    else
        echo "❌ Batch $batch failed - check logs"
        read -p "Continue with next batch? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "🛑 Migration stopped by user"
            exit 1
        fi
    fi
    
    # Delay between batches (except for the last one)
    if [ $batch -lt $TOTAL_BATCHES ]; then
        echo "⏳ Waiting $DELAY_MINUTES minutes before next batch..."
        sleep ${DELAY_MINUTES}m
    fi
done

echo ""
echo "🎉 All batches completed!"
echo "📊 Run './run.sh info' to see final migration statistics"
```

Make it executable and run:
```bash
chmod +x batch_migrate.sh
./batch_migrate.sh
```

### Advanced Batching Strategies

#### Priority-Based Migration
Migrate most important issues first:

```bash
# High priority issues first
./run.sh $FLAGS migrate-jql "project = PROJ AND priority in (Blocker, Critical, High)" --max-results 50

# Medium priority 
./run.sh $FLAGS migrate-jql "project = PROJ AND priority = Medium" --max-results 100

# Low priority last
./run.sh $FLAGS migrate-jql "project = PROJ AND priority in (Low, Trivial)" --max-results 100
```

#### Component-Based Batching
Migrate by team or component:

```bash
# Frontend issues
./run.sh $FLAGS migrate-jql "project = PROJ AND component = Frontend" --max-results 75

# Backend issues  
./run.sh $FLAGS migrate-jql "project = PROJ AND component = Backend" --max-results 75

# API issues
./run.sh $FLAGS migrate-jql "project = PROJ AND component = API" --max-results 50
```

#### Status-Based Migration
Logical migration order:

```bash
# 1. Closed issues first (less likely to change)
./run.sh $FLAGS --migrate-closed-as-closed migrate-jql "project = PROJ AND status in (Done, Closed, Resolved, 'Won\'t Fix')" --max-results 100

# 2. In-progress issues (might need attention)
./run.sh $FLAGS migrate-jql "project = PROJ AND status in ('In Progress', 'Code Review')" --max-results 50

# 3. Open issues last (most active)
./run.sh $FLAGS migrate-jql "project = PROJ AND status in (Open, 'To Do', Backlog)" --max-results 75
```

### Monitoring and Recovery

#### Check Rate Limit Status
```bash
# Check GitHub API rate limit
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Show remaining requests
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit | jq '.rate.remaining'
```

#### Resume Failed Batches
If a batch fails, you can resume by excluding already migrated issues:

```bash
# Get list of migrated issues (assuming they have the migrated-from-jira label)
# Then exclude them from next batch
./run.sh $FLAGS migrate-jql "project = PROJ AND key >= PROJ-101 AND key <= PROJ-200"
```

#### Dry Run Before Each Batch
Always preview large batches:

```bash
# Preview the batch first
./run.sh --dry-run $FLAGS migrate-jql "project = PROJ AND created >= '2023-01-01' AND created <= '2023-03-31'"

# If preview looks good, run actual migration
./run.sh $FLAGS migrate-jql "project = PROJ AND created >= '2023-01-01' AND created <= '2023-03-31'"
```

### Enhanced Bulk Migration

For the brave souls with good API limits:

```bash
# Migrate entire project with enhancements (use with caution!)
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate-project PROJ

# Safer: Limit bulk migration size
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels migrate-jql "project = PROJ" --max-results 200
```

### Preview Enhanced Migration

```bash
# Preview what would be enhanced
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed preview PROJ-123

# Full preview with body content
./run.sh --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed preview --full PROJ-123
```

## What Gets Enhanced

### 🧑‍💻 User Mapping
- **Assignees**: Jira assignees → GitHub assignees
- **Comments**: Enhanced attribution with @mentions
  ```
  ### Comment by @johndoe-dev (originally John Doe) on 2023-01-15
  
  This looks good to merge!
  ```
- **Issue Body**: Assignee info includes GitHub mentions

### 🏷️ Label Enhancement
- **Issue Types**: `type:bug`, `type:feature`, `type:task`, etc.
- **Priorities**: `priority:high`, `priority:medium`, `priority:low`
- **Status**: `status:done`, `status:in-progress`, `status:todo`
- **Components**: `component:frontend`, `component:api`, `component:ui`
- **Auto-creation**: Missing labels are created with appropriate colors

### 🔒 Closed Issue Migration
- **Status Mapping**: 
  - `Done/Resolved/Closed` → GitHub `closed` state
  - `Open/In Progress/To Do` → GitHub `open` state
- **Preserves History**: Original Jira status shown in issue metadata

## Enhanced Output

Enhanced migrations show detailed progress:

```
🚀 Starting enhanced migration of 3 issues...

Enhancement Configuration
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Feature              ┃ Status    ┃ Details                               ┃
┃ User Mapping         ┃ ✅ Enabled ┃ 23/47 users mapped (48.9%)          ┃
┃ Enhanced Labels      ┃ ✅ Enabled ┃ Auto-create: True                    ┃
┃ Closed Issue Migration ┃ ✅ Enabled ┃ Migrating resolved issues as closed   ┃
└──────────────────────┴───────────┴───────────────────────────────────────┘

✅ PROJ-123 → #1 (assignee mapped (John Doe → @johndoe-dev); 4 labels auto-created; migrated as closed (was Done))
✅ PROJ-124 → #2 (3 labels enhanced; 2 GitHub @mentions created in comments)
✅ PROJ-125 → #3 (5 labels auto-created)

📊 Migration Summary
✅ Successful: 3
❌ Failed: 0

🚀 Enhancement Summary
👤 2 assignees mapped to GitHub users
🏷️  7 unique labels auto-created
🔒 1 issues migrated as closed
💬 5 GitHub @mentions created in comments

👥 User Mapping Summary
2/3 users mapped (66.7% success rate), 2 assignees, 3 commenters, 5 new @mentions created

🏷️  Label Enhancement Summary
6 original labels; 18 enhanced labels added (type, priority, status, component); 7 labels auto-created
```

## Best Practices

### 🎯 User Mapping Priority
1. **Start with most active users** - The generated file sorts by activity
2. **Focus on assignees and frequent commenters**
3. **Map project leads and key contributors first**

### 🏷️ Label Strategy
- Use `--auto-create-labels` for consistent labeling
- Review created labels after first migration
- Customize label colors via `label_manager.py` if needed

### 🔒 Closed Issues
- Use `--migrate-closed-as-closed` to preserve issue lifecycle
- Test with a few issues first to verify status mapping
- Consider filtering JQL to exclude very old resolved issues

### 🧪 Testing Workflow
1. **Always preview first**: `./run.sh --dry-run ...`
2. **Start small**: Test with 1-2 issues before bulk migration
3. **Check GitHub**: Verify assignees, labels, and @mentions work
4. **Iterate mapping**: Add more users and re-run as needed

## Troubleshooting

### User Mapping Issues
```bash
# Check mapping file validity
./run.sh validate-user-mapping user-mapping-proj.json

# See which users still need mapping
./run.sh show-mapping-stats user-mapping-proj.json
```

### Label Creation Issues
- Ensure GitHub token has repository write permissions
- Check for existing labels that might conflict
- Run with `--dry-run` first to see what labels would be created

### Connection Issues
```bash
# Test basic connectivity
./run.sh test-connection

# Show current configuration
./run.sh info
```

## Migration Results

Your GitHub issues will have:

- ✅ **Proper assignees** mapped from Jira
- ✅ **Rich labels** showing type, priority, status, components
- ✅ **Correct state** (open/closed) based on Jira status  
- ✅ **Enhanced comments** with GitHub @mentions
- ✅ **Complete metadata** from original Jira issue
- ✅ **Migration tracking** with `migrated-from-jira` label

This creates a much more useful and connected GitHub issue that maintains the context and relationships from your original Jira project!