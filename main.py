#!/usr/bin/env python3
"""
Jira to GitHub Issues Migration Tool

This tool helps migrate Jira issues to GitHub issues with proper formatting,
labels, and metadata preservation.
"""

import click
from typing import List, Optional
from config import Config
from migration_service import MigrationService
from rich import print as rprint
from rich.console import Console
import sys
import re


def extract_issue_key_from_url_or_key(input_string: str) -> str:
    """
    Extract issue key from either a Jira URL or a plain issue key.
    
    Examples:
    - "https://company.atlassian.net/browse/PROJ-123" -> "PROJ-123"
    - "PROJ-123" -> "PROJ-123"
    """
    # Check if it's a URL containing /browse/
    url_pattern = r'https?://[^/]+/browse/([A-Z]+-\d+)'
    match = re.search(url_pattern, input_string)
    if match:
        return match.group(1)
    
    # Check if it's already a plain issue key (PROJECT-123 format)
    key_pattern = r'^[A-Z]+-\d+$'
    if re.match(key_pattern, input_string):
        return input_string
    
    # If neither pattern matches, return as-is and let the service handle the error
    return input_string


@click.group()
@click.option('--dry-run', is_flag=True, help='Preview changes without creating issues')
@click.option('--no-comments', is_flag=True, help='Skip migrating comments')
@click.option('--no-attachments', is_flag=True, help='Skip migrating attachments and images')
@click.option('--user-mapping-file', help='Path to user mapping JSON file for enhanced migration')
@click.option('--auto-create-labels', is_flag=True, help='Automatically create missing labels for types, priorities, etc.')
@click.option('--migrate-closed-as-closed', is_flag=True, help='Migrate resolved Jira issues as closed GitHub issues')
@click.option('--failed-issues-file', help='Output file for failed issue details (JSON format)')
@click.pass_context
def cli(ctx, dry_run: bool, no_comments: bool, no_attachments: bool,
        user_mapping_file: str, auto_create_labels: bool, migrate_closed_as_closed: bool,
        failed_issues_file: str):
    """Jira to GitHub Issues Migration Tool"""
    try:
        config = Config.from_env()
        config.dry_run = dry_run
        config.include_comments = not no_comments
        config.include_attachments = not no_attachments
        
        # Store enhancement options in context for commands
        ctx.obj = {
            'config': config,
            'user_mapping_file': user_mapping_file,
            'auto_create_labels': auto_create_labels,
            'migrate_closed_as_closed': migrate_closed_as_closed,
            'failed_issues_file': failed_issues_file,
            'use_enhanced': bool(user_mapping_file or auto_create_labels or migrate_closed_as_closed)
        }
    except ValueError as e:
        rprint(f"[bold red]Configuration Error:[/bold red] {e}")
        rprint("\n[yellow]Please create a .env file with the required environment variables.[/yellow]")
        rprint("[yellow]See .env.example for reference.[/yellow]")
        sys.exit(1)


@cli.command()
@click.argument('issue_keys', nargs=-1, required=True)
@click.pass_context
def migrate(ctx, issue_keys: List[str]):
    """Migrate specific Jira issues by their keys or URLs (e.g., PROJ-123 or https://company.atlassian.net/browse/PROJ-123)"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    # Extract issue keys from URLs if provided
    processed_keys = [extract_issue_key_from_url_or_key(key) for key in issue_keys]
    
    if config.dry_run:
        rprint("[yellow]Running in dry-run mode - no issues will be created[/yellow]")
    
    # Use enhanced service if any enhancements are requested
    if ctx_data['use_enhanced']:
        from migration_extensions import EnhancedMigrationService
        service = EnhancedMigrationService(
            config,
            ctx_data['user_mapping_file'],
            ctx_data['auto_create_labels'],
            ctx_data['migrate_closed_as_closed']
        )
    else:
        service = MigrationService(config, ctx_data['failed_issues_file'])
    
    results = service.migrate_issues_by_keys(processed_keys)
    
    # Exit with error code if any migrations failed
    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        sys.exit(1)


@cli.command()
@click.argument('jql')
@click.option('--max-results', default=50, help='Maximum number of issues to migrate')
@click.option('--start-at', default=0, help='Starting offset for pagination (0-based)')
@click.pass_context
def migrate_jql(ctx, jql: str, max_results: int, start_at: int):
    """Migrate issues found by JQL query"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    if config.dry_run:
        rprint("[yellow]Running in dry-run mode - no issues will be created[/yellow]")
    
    # Use enhanced service if any enhancements are requested
    if ctx_data['use_enhanced']:
        from migration_extensions import EnhancedMigrationService
        service = EnhancedMigrationService(
            config,
            ctx_data['user_mapping_file'],
            ctx_data['auto_create_labels'],
            ctx_data['migrate_closed_as_closed']
        )
    else:
        service = MigrationService(config, ctx_data['failed_issues_file'])
    
    results = service.migrate_issues_by_jql(jql, max_results, start_at)
    
    # Exit with error code if any migrations failed
    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        sys.exit(1)


@cli.command()
@click.argument('project_key')
@click.option('--status', help='Filter by issue status')
@click.pass_context
def migrate_project(ctx, project_key: str, status: Optional[str]):
    """Migrate all issues from a Jira project"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    if config.dry_run:
        rprint("[yellow]Running in dry-run mode - no issues will be created[/yellow]")
    
    # Use enhanced service if any enhancements are requested
    if ctx_data['use_enhanced']:
        from migration_extensions import EnhancedMigrationService
        service = EnhancedMigrationService(
            config,
            ctx_data['user_mapping_file'],
            ctx_data['auto_create_labels'],
            ctx_data['migrate_closed_as_closed']
        )
    else:
        service = MigrationService(config, ctx_data['failed_issues_file'])
    
    results = service.migrate_project_issues(project_key, status)
    
    # Exit with error code if any migrations failed
    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        sys.exit(1)


@cli.command()
@click.argument('issue_keys', nargs=-1, required=True)
@click.option('--full', is_flag=True, help='Show full body content')
@click.pass_context
def preview(ctx, issue_keys: List[str], full: bool):
    """Preview what would be migrated without creating issues"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    # Extract issue keys from URLs if provided
    processed_keys = [extract_issue_key_from_url_or_key(key) for key in issue_keys]
    
    # Use enhanced service if any enhancements are requested
    if ctx_data['use_enhanced']:
        from migration_extensions import EnhancedMigrationService
        service = EnhancedMigrationService(
            config,
            ctx_data['user_mapping_file'],
            ctx_data['auto_create_labels'],
            ctx_data['migrate_closed_as_closed']
        )
    else:
        service = MigrationService(config, ctx_data['failed_issues_file'])
    
    service.preview_migration(processed_keys, show_full=full)


@cli.command()
@click.pass_context
def test_connection(ctx):
    """Test connection to Jira and GitHub"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    console = Console()
    
    # Test Jira connection
    try:
        from jira_client import JiraClient
        jira_client = JiraClient(config)
        
        # Try to get server info or a simple query
        test_issues = jira_client.search_issues("ORDER BY created DESC", max_results=1)
        rprint("[green]✓ Jira connection successful[/green]")
        
        if config.default_jira_project:
            project_issues = jira_client.get_project_issues(config.default_jira_project)
            rprint(f"[green]✓ Found {len(project_issues)} issues in project {config.default_jira_project}[/green]")
        
    except Exception as e:
        rprint(f"[red]✗ Jira connection failed: {e}[/red]")
    
    # Test GitHub connection
    try:
        from github_client import GitHubClient
        github_client = GitHubClient(config)
        
        # Try to get repository info
        labels = github_client.get_repo_labels()
        milestones = github_client.get_repo_milestones()
        
        rprint(f"[green]✓ GitHub connection successful[/green]")
        rprint(f"[green]✓ Repository: {config.github_repo_owner}/{config.github_repo_name}[/green]")
        rprint(f"[green]✓ Found {len(labels)} labels and {len(milestones)} milestones[/green]")
        
    except Exception as e:
        rprint(f"[red]✗ GitHub connection failed: {e}[/red]")


@cli.command()
@click.pass_context
def info(ctx):
    """Show configuration information"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    console = Console()
    
    from rich.table import Table
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Jira Server", config.jira_server_url)
    table.add_row("Jira Email", config.jira_email)
    table.add_row("GitHub Repository", f"{config.github_repo_owner}/{config.github_repo_name}")
    table.add_row("Default Jira Project", config.default_jira_project or "Not set")
    table.add_row("Include Comments", "Yes" if config.include_comments else "No")
    table.add_row("Include Attachments", "Yes" if config.include_attachments else "No")
    table.add_row("Dry Run", "Yes" if config.dry_run else "No")
    
    console.print(table)


# New user discovery commands
@cli.command('generate-user-mapping')
@click.argument('project_key')
@click.option('--output-file', help='Output file path (default: user-mapping-{project}.json)')
@click.pass_context
def generate_user_mapping(ctx, project_key: str, output_file: str):
    """Generate user mapping template file for a Jira project"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    from user_discovery import UserDiscoveryService
    discovery_service = UserDiscoveryService(config)
    
    result_file = discovery_service.generate_user_mapping_template(project_key, output_file)
    
    if not result_file:
        sys.exit(1)


@cli.command('validate-user-mapping')
@click.argument('mapping_file')
@click.pass_context
def validate_user_mapping(ctx, mapping_file: str):
    """Validate a user mapping file"""
    ctx_data = ctx.obj
    config = ctx_data['config']
    
    from user_discovery import UserDiscoveryService
    discovery_service = UserDiscoveryService(config)
    
    is_valid = discovery_service.validate_mapping_file(mapping_file)
    
    if not is_valid:
        sys.exit(1)


@cli.command('show-mapping-stats')
@click.argument('mapping_file')
@click.pass_context
def show_mapping_stats(ctx, mapping_file: str):
    """Show statistics about a user mapping file"""
    ctx_data = ctx.obj
    config = ctx_data['config']

    from user_discovery import UserDiscoveryService
    discovery_service = UserDiscoveryService(config)

    discovery_service.show_mapping_stats(mapping_file)


@cli.command('count-issues')
@click.argument('jql')
@click.option('--estimate-from-max', is_flag=True, help='Estimate count from highest issue number')
@click.pass_context
def count_issues(ctx, jql: str, estimate_from_max: bool):
    """Count total issues matching a JQL query"""
    ctx_data = ctx.obj
    config = ctx_data['config']

    from jira_client import JiraClient
    jira_client = JiraClient(config)

    try:
        if estimate_from_max:
            # Get the highest issue number by sorting descending and taking first result
            # Remove any existing ORDER BY clause and add our own
            import re
            base_jql = re.sub(r'\s+ORDER\s+BY\s+.*$', '', jql, flags=re.IGNORECASE).strip()
            max_jql = base_jql + " ORDER BY key DESC"
            issues = jira_client.search_issues(max_jql, max_results=1)
            if issues:
                highest_key = issues[0].key
                # Extract number from key (e.g., "YSP-1170" -> 1170)
                import re
                match = re.search(r'-(\d+)$', highest_key)
                if match:
                    max_number = int(match.group(1))
                    rprint(f"[green]Estimated {max_number} issues (based on highest key: {highest_key})[/green]")
                    rprint(f"[yellow]Note: This is an estimate based on the highest issue number[/yellow]")
                    rprint(f"[blue]JQL: {jql}[/blue]")
                    return
                else:
                    rprint(f"[yellow]Could not extract number from key: {highest_key}[/yellow]")
            else:
                rprint(f"[red]No issues found for estimation[/red]")
                sys.exit(1)

        # Fall back to regular counting
        count = jira_client.get_issue_count(jql)
        rprint(f"[green]Found {count} issues matching query[/green]")
        rprint(f"[blue]JQL: {jql}[/blue]")
    except Exception as e:
        rprint(f"[red]Error counting issues: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cli()
