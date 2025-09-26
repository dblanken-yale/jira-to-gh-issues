# Jira to GitHub Issues Migration Tool

A comprehensive Python tool for migrating Jira issues to GitHub with advanced user mapping, label enhancement, and state preservation.

## ✨ Features

### Core Migration
-   🎯 **Selective Migration**: Migrate specific issues by key, JQL query, or entire projects
-   🏷️ **Smart Labels**: Enhanced label system with auto-creation for types, priorities, and components
-   💬 **Comment Migration**: Preserves comments with enhanced GitHub user attribution
-   🔗 **Markup Conversion**: Converts Jira markup to GitHub markdown
-   🧪 **Dry Run Mode**: Preview migrations without creating actual issues

### Enhanced Migration (NEW!)
-   👥 **User Mapping**: Auto-discover project users and map Jira users to GitHub users
-   🎯 **Assignee Migration**: Properly assign GitHub users based on Jira assignees  
-   💬 **@Mention Comments**: Comments include GitHub @mentions with original attribution
-   🏷️ **Auto-Label Creation**: Automatically creates labels for issue types, priorities, statuses, and components
-   🔒 **State Migration**: Migrate resolved Jira issues as closed GitHub issues
-   📊 **Comprehensive Statistics**: Detailed reporting on enhancements and mapping success rates

## Setup

### 1. Install deps

Run the setup script to automate the setup process:

```bash
python3 setup.py
```

This will:

-   Ensure a virtual environment exists
-   Install dependencies from `requirements.txt`
-   Copy `.env.example` into `.env`

**Alternatively, you can perform the steps manually:**

1. Set up a virtual environment:

    ```bash
    python3 -m venv .venv
    ```

2. Install dependencies:

    ```bash
    .venv/bin/pip install -r requirements.txt
    ```

3. Create a `.env`:

    ```bash
    cp .env.example .env
    ```

### 2. Credentials

Grab your tokens from [Atlassian here](https://id.atlassian.com/manage-profile/security/api-tokens) and from [GitHub here](https://github.com/settings/personal-access-tokens) and put them into [`.env`](./.env).

### 3. Test the connections:

```bash
./run test-connection
```

## Usage

### Quick Start

```bash
./run info
./run test-connection
```

> [!TIP]
> You can use either issue keys (`PROJ-123`) or full Jira URLs (`https://company.atlassian.net/browse/PROJ-123`) in all commands that accept issue identifiers.

## Enhanced Migration Workflow

### Step 1: Generate User Mapping (Recommended)

Automatically discover all users in your Jira project:

```bash
# Generate user mapping template for project
./run generate-user-mapping PROJ

# Custom output file
./run generate-user-mapping PROJ --output-file my-users.json
```

This creates `user-mapping-proj.json` with all discovered users. Edit this file to add GitHub usernames:

```json
{
  "user_mapping": {
    "john.doe@company.com": {
      "display_name": "John Doe",
      "github_username": "johndoe",  // ← Add GitHub username
      "issue_activity_count": 89
    }
  }
}
```

### Step 2: Validate and Check Mapping

```bash
# Validate your mapping file
./run validate-user-mapping user-mapping-proj.json

# Show mapping statistics  
./run show-mapping-stats user-mapping-proj.json
```

### Step 3: Enhanced Migration

Run migrations with powerful enhancements:

```bash
# Enhanced migration with all features
./run --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate PROJ-123

# Bulk enhanced migration
./run --user-mapping-file=user-mapping-proj.json --auto-create-labels --migrate-closed-as-closed migrate-project PROJ
```

## Migration Options

### Basic Migration

```bash
# Simple migration
./run migrate PROJ-123 PROJ-124

# Preview before migrating
./run preview PROJ-123 PROJ-124
./run --dry-run migrate PROJ-123 PROJ-124

# Migrate without comments/attachments
./run --no-comments migrate PROJ-123 PROJ-124
./run --no-attachments migrate PROJ-123 PROJ-124
```

### Enhanced Migration Flags

| Flag | Description | Benefit |
|------|-------------|---------|
| `--user-mapping-file=FILE` | Map Jira users to GitHub users | Proper assignees & @mentions |
| `--auto-create-labels` | Auto-create labels for types, priorities, etc. | Rich GitHub labeling |
| `--migrate-closed-as-closed` | Migrate resolved issues as closed | Preserves issue lifecycle |

### Migration Commands

```bash
# Migrate specific issues (with enhancements)
./run --user-mapping-file=users.json migrate PROJ-123 PROJ-124

# Migrate by JQL query
./run --auto-create-labels migrate-jql "project = PROJ AND status = 'To Do'"

# Migrate by JQL query with pagination (for large result sets)
./run --auto-create-labels migrate-jql "project = PROJ ORDER BY key ASC" --max-results 50 --start-at 0
./run --auto-create-labels migrate-jql "project = PROJ ORDER BY key ASC" --max-results 50 --start-at 50

# Migrate entire project
./run --user-mapping-file=users.json --migrate-closed-as-closed migrate-project PROJ

# Filter by status
./run migrate-project PROJ --status "Done"
```

### Enhanced Preview

```bash
# Preview with enhancements
./run --user-mapping-file=users.json --auto-create-labels preview PROJ-123

# Full preview with issue body
./run --user-mapping-file=users.json preview --full PROJ-123
```

## ⚠️ Important: Using the Correct Python Environment

We use a virtual environment to manage dependencies. Use one of the following to run the tool:

### Method 1: Use the provided run script (Recommended)

```bash
./run.sh test-connection
```

### Method 2: Use the full Python path

```bash
./.venv/bin/python main.py test-connection
```

### Method 3: Activate the virtual environment first

```bash
source .venv/bin/activate
python main.py test-connection
```

## 🔄 Issue Mapping

### Enhanced GitHub Issues Include:

**📋 Issue Structure:**
-   **Title**: `[JIRA-KEY] Original Summary`
-   **State**: `open` or `closed` (based on Jira status when `--migrate-closed-as-closed` used)
-   **Assignees**: 🆕 Mapped from Jira users (when user mapping provided)

**📝 Issue Body:**
-   Link back to original Jira issue
-   Converted description (Jira markup → Markdown) 
-   Enhanced metadata with original assignee and GitHub mapping info
-   📎 Attachment links with download instructions
-   💬 Comments with GitHub @mentions: `@johndoe (originally John Doe)`

**🏷️ Enhanced Labels (when `--auto-create-labels` used):**
-   **Original**: Preserves existing Jira labels
-   **Types**: `type:bug`, `type:feature`, `type:task`, `type:story`
-   **Priorities**: `priority:high`, `priority:medium`, `priority:low` 
-   **Status**: `status:todo`, `status:in-progress`, `status:done`
-   **Components**: `component:frontend`, `component:api`, `component:ui`
-   **Migration**: `migrated-from-jira` (always added)

### 👥 User Mapping Results

**With User Mapping File:**
- ✅ **Assignees**: Jira assignees become GitHub assignees
- ✅ **@Mentions**: Comments include `### Comment by @github-user (originally Jira User)`
- ✅ **Issue Body**: Shows both original and mapped assignee info

**Without User Mapping:**
- ❌ **Assignees**: Not migrated (original behavior)
- ℹ️ **Comments**: Show original Jira usernames only

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DRY_RUN` | Preview mode | `false` |
| `INCLUDE_COMMENTS` | Migrate comments | `true` |
| `INCLUDE_ATTACHMENTS` | Migrate attachments | `true` |

### Command Line Flags (New!)

| Flag | Description | What It Enables |
|------|-------------|----------------|
| `--user-mapping-file=FILE` | Path to user mapping JSON | • Proper assignee migration<br>• @mentions in comments |
| `--auto-create-labels` | Auto-create enhanced labels | • Type, priority, status labels<br>• Automatic GitHub label creation |
| `--migrate-closed-as-closed` | Migrate resolved issues as closed | • Preserves issue lifecycle state |
| `--max-results=N` | Number of issues per batch | • Control batch size (default: 50) |
| `--start-at=N` | Starting offset for pagination | • Resume from specific point<br>• Manual pagination control |
| `--dry-run` | Preview without creating issues | • Safe testing before migration |
| `--no-comments` | Skip comment migration | • Faster migration, metadata only |
| `--no-attachments` | Skip attachment processing | • Faster migration |

## 📊 Migration Statistics

Enhanced migrations provide detailed statistics:

```
🚀 Enhancement Summary
👤 12 assignees mapped to GitHub users
🏷️ 28 unique labels auto-created  
🔒 15 issues migrated as closed
💬 47 GitHub @mentions created in comments

👥 User Mapping Summary
34/47 users mapped (72.3% success rate), 12 assignees, 22 commenters, 47 new @mentions created

🏷️ Label Enhancement Summary  
89 original labels; 156 enhanced labels added (type, priority, status, component); 28 labels auto-created
```

## Troubleshooting

### Basic Debugging

-   Use `--dry-run` to test without creating issues
-   Check `./run test-connection` for connectivity issues
-   Use `./run info` to verify configuration

### Enhanced Migration Issues

**User Mapping Problems:**
```bash
# Validate mapping file format
./run validate-user-mapping user-mapping-proj.json

# Check mapping statistics and find unmapped users
./run show-mapping-stats user-mapping-proj.json

# Regenerate mapping if needed
./run generate-user-mapping PROJ --output-file new-mapping.json
```

**Label Creation Issues:**
- Ensure GitHub token has repository write permissions
- Check for existing labels that might conflict  
- Use `--dry-run` first to preview label creation
- Run without `--auto-create-labels` if you prefer manual label management

**User Discovery Issues:**
- Verify Jira permissions allow reading project roles and user lists
- Check if your Jira instance restricts user enumeration
- Try with a smaller project first to test functionality

**Permission Issues:**
- **GitHub**: Token needs `repo` scope for private repositories, `public_repo` for public ones
- **Jira**: Account needs read access to projects, issues, and user information

## Examples & Best Practices

### 🚀 Complete Enhanced Migration Workflow

See [`examples/enhanced_migration_workflow.md`](examples/enhanced_migration_workflow.md) for a comprehensive step-by-step guide.

### 📝 Example User Mapping File

```json
{
  "_metadata": {
    "project": "PROJ", 
    "total_users": 12,
    "sources_used": ["assignable", "issue_history", "role_member"]
  },
  "user_mapping": {
    "john.doe@company.com": {
      "display_name": "John Doe",
      "github_username": "johndoe",
      "issue_activity_count": 89,
      "roles": ["Developers"]
    }
  }
}
```

### 🎯 Migration Best Practices

**1. Start with User Discovery:**
```bash
# Always generate user mapping first
./run generate-user-mapping PROJ
# Edit file to add GitHub usernames  
# Validate before using
./run validate-user-mapping user-mapping-proj.json
```

**2. Test Before Bulk Migration:**
```bash  
# Test with a few issues first
./run --user-mapping-file=users.json --auto-create-labels --dry-run migrate PROJ-123

# Then migrate test issues
./run --user-mapping-file=users.json --auto-create-labels migrate PROJ-123 PROJ-124

# Finally bulk migrate
./run --user-mapping-file=users.json --auto-create-labels migrate-project PROJ
```

**3. Iterative Mapping:**
- Focus on most active users first (file is pre-sorted by activity)
- Start with assignees and frequent commenters
- Add more users over time and re-run migrations

## 🔗 Advanced Features

### User Discovery Sources
The tool discovers users from multiple sources:
- **Project Roles**: Users assigned to project roles (Admin, Developer, etc.)
- **Assignable Users**: Users who can be assigned to project issues  
- **Issue History**: All users who have reported, been assigned, or commented on issues

### Label Auto-Creation
Labels are created with smart color coding:
- **Types**: Blue (`type:bug`, `type:feature`)  
- **Priorities**: Red to green scale (`priority:high`, `priority:low`)
- **Status**: Green (`status:done`), yellow (`status:in-progress`)
- **Components**: Purple (`component:frontend`, `component:api`)

### State Migration Logic
Issues are migrated as `closed` when `--migrate-closed-as-closed` is used and Jira status is:
- Done, Closed, Resolved, Complete, Fixed, Won't Fix, Duplicate, Invalid, Cannot Reproduce, Rejected, Abandoned

## Attachment Handling

Currently, the GitHub API does not allow adding attachments to issues programmatically. Since Jira requires authentication to access attachments, we cannot directly link to them in GitHub issues.

**Current Solution:**
- Original Jira attachment links are preserved in issue body
- Manual disclaimer explains attachments need manual migration
- Download instructions provided for each attachment

## 📦 Batch Migration Tools

For large-scale migrations, use the provided batch migration scripts to handle GitHub API rate limits:

### Quick Range Migration

Migrate sequential issue ranges (e.g., PROJ-1 to PROJ-100):

```bash
# Copy script to project root
cp examples/range_migrate.sh .
chmod +x range_migrate.sh

# Migrate PROJ-1 to PROJ-500 in batches of 50
./range_migrate.sh PROJ 1 500 50 15

# This creates batches like:
# Batch 1: PROJ-1 to PROJ-50
# Batch 2: PROJ-51 to PROJ-100  
# Batch 3: PROJ-101 to PROJ-150
# ... with 15-minute delays between batches
```

### Smart Batch Migration ✨ FIXED!

Intelligent batching with **proper pagination** - now migrates ALL issues instead of repeating the same ones:

```bash
# Copy script to project root
cp examples/batch_migrate.sh .
chmod +x batch_migrate.sh

# Run interactive batch migration
./batch_migrate.sh PROJ 50 10

# Choose from strategies:
# 1. Migrate all issues (✅ now paginated correctly)
# 2. Migrate by status (closed first, then open)
# 3. Migrate by priority (high to low)
# 4. Migrate by date range
# 5. Custom JQL query

# Each batch now processes unique issues:
# Batch 1: Issues 1-50 (start_at=0)
# Batch 2: Issues 51-100 (start_at=50)
# Batch 3: Issues 101-150 (start_at=100)
```

### Manual Batch Commands

For more control, use manual batch commands with proper pagination:

```bash
# Method 1: Sequential ranges (still useful for known ranges)
for i in {1..50}; do echo "PROJ-$i"; done | xargs ./run.sh --user-mapping-file=users.json --auto-create-labels migrate
for i in {51..100}; do echo "PROJ-$i"; done | xargs ./run.sh --user-mapping-file=users.json --auto-create-labels migrate

# Method 2: JQL-based batching with pagination (✅ RECOMMENDED)
./run.sh --user-mapping-file=users.json --auto-create-labels migrate-jql "project = PROJ ORDER BY key ASC" --max-results 50 --start-at 0
./run.sh --user-mapping-file=users.json --auto-create-labels migrate-jql "project = PROJ ORDER BY key ASC" --max-results 50 --start-at 50
./run.sh --user-mapping-file=users.json --auto-create-labels migrate-jql "project = PROJ ORDER BY key ASC" --max-results 50 --start-at 100

# Method 3: Status-based batching with pagination
./run.sh --user-mapping-file=users.json --migrate-closed-as-closed migrate-jql "project = PROJ AND status in (Done, Closed) ORDER BY key ASC" --max-results 50 --start-at 0
./run.sh --user-mapping-file=users.json --migrate-closed-as-closed migrate-jql "project = PROJ AND status in (Done, Closed) ORDER BY key ASC" --max-results 50 --start-at 50

# Method 4: Date-based batching
./run.sh --user-mapping-file=users.json --auto-create-labels migrate-jql "project = PROJ AND created >= '2023-01-01' AND created <= '2023-03-31' ORDER BY key ASC" --max-results 50 --start-at 0
```

**Batch Size Recommendations:**
- **25-50 issues**: For comprehensive migrations with comments and attachments
- **50-100 issues**: For simple migrations without comments
- **10-15 minute delays**: Between large batches to respect rate limits

See [`examples/enhanced_migration_workflow.md`](examples/enhanced_migration_workflow.md) for complete batch migration documentation.

## 🚨 Error Handling & Failed Issues

### Automatic Error Handling

The migration tool now includes robust error handling for common issues:

- **Rate Limits**: Automatic retry with exponential backoff (30s, 60s, 120s, 240s, 480s)
- **GitHub API Errors**: Smart retry logic for temporary failures
- **Permission Issues**: Clear error messages for authentication problems
- **Network Errors**: Automatic retry for connection issues

### Failed Issues Logging

Track and retry failed migrations with detailed error logs:

```bash
# Enable failed issues logging
./run.sh --failed-issues-file=failed.json migrate PROJ-123 PROJ-124

# Batch migrations automatically create timestamped logs
./examples/batch_migrate.sh PROJ 50 10
# Creates: failed-issues-20231225-143022.json
```

### Failed Issues File Format

```json
{
  "timestamp": "2023-12-25T14:30:22.123456",
  "total_failed": 3,
  "failed_issues": [
    {
      "jira_key": "PROJ-123",
      "error_message": "403 Forbidden: Rate limit exceeded",
      "timestamp": "2023-12-25T14:30:22.456789"
    }
  ]
}
```

### Retrying Failed Issues

```bash
# Extract failed issue keys from JSON log
jq -r '.failed_issues[].jira_key' failed.json

# Retry specific failed issues
./run.sh --user-mapping-file=users.json migrate PROJ-123 PROJ-456

# Retry with different settings (e.g., no comments for faster processing)
./run.sh --no-comments migrate PROJ-123 PROJ-456
```

### Common Issues & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `403 Forbidden` | Rate limits or bad token | Automatic exponential backoff: 30s→60s→120s→240s→480s |
| `422 Unprocessable Entity` | Invalid issue data | Check issue title/body content, review logs |
| `404 Not Found` | Repository access | Verify repo name and token permissions |
| `Max retries exceeded` | Persistent API issues | Check GitHub status, try smaller batches |
