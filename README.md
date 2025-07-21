# Jira to GitHub Issues Migration Tool

A Python tool for automating the migration of Jira issues to GitHub issues.

## Features

-   🎯 **Selective Migration**: Migrate specific issues by key, JQL query, or entire projects
-   🏷️ **Labels**: Preserves original Jira labels
-   💬 **Comment Migration**: Optionally migrate Jira comments to GitHub issue descriptions
-   🔗 **Markup Conversion**: Converts Jira markup to GitHub markdown
-   🧪 **Dry Run Mode**: Preview migrations without creating actual issues

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

### Show Configuration

```bash
./run info
./run test-connection
```

> [!TIP]
> You can use either issue keys (`PROJ-123`) or full Jira URLs (`https://company.atlassian.net/browse/PROJ-123`) in all commands that accept issue identifiers.

### Preview Migration (Dry Run)

```bash
# Preview specific issues by key
./run preview PROJ-123 PROJ-124

# Preview with dry-run flag
./run --dry-run migrate PROJ-123 PROJ-124
```

### Migrate Specific Issues

```bash
# Migrate by issue keys/urls
./run migrate PROJ-123 https://company.atlassian.net/browse/PROJ-124

# Migrate without comments
./run --no-comments migrate PROJ-123 PROJ-124

# Migrate without attachments
./run --no-comments migrate PROJ-123 PROJ-124
```

### Migrate by JQL Query

```bash
# Migrate issues matching JQL
./run migrate-jql "project = PROJ AND status = 'To Do'"

# Limit results
./run migrate-jql "assignee = currentUser()" --max-results 10
```

### Migrate Entire Project

```bash
# Migrate all issues from a project
./run migrate-project PROJ

# Migrate only specific status
./run migrate-project PROJ --status "To Do"
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

## Mapping

Issue type, priority, status, and component information is included in the issue body's metadata table.

GitHub issues are created with:

-   **Title**: `[JIRA-KEY] Original Summary`
-   **Body**:
    -   Link back to original Jira issue
    -   Converted description (Jira markup → Markdown)
    -   Metadata table (type, priority, status, etc.)
    -   Comments (if enabled)
-   **Labels**: Mapped from Jira
-   **Assignees**: Ignored, as we don't have a way of reliably mapping the usernames

## Configuration Options

| Environment Variable  | Description         | Default |
| --------------------- | ------------------- | ------- |
| `DRY_RUN`             | Preview mode        | `false` |
| `INCLUDE_COMMENTS`    | Migrate comments    | `true`  |
| `INCLUDE_ATTACHMENTS` | Migrate attachments | `true`  |

## Troubleshooting

### Debugging

-   Use `--dry-run` to test without creating issues
-   Check `./run test-connection` for connectivity issues
-   Use `./run info` to verify configuration

## Attachment Handling

Currently, the GitHub API does not allow to add attachments to issues programmatically.
Since jira requires auth to load attachments we can't just put the same links into the GitHub issue,
leaving us with no easy way to migrate attachments.

For now we simply provide the original link and add a disclaimer that attachments must be migrated manually.
