from typing import List, Dict, Any
from jira_client import JiraClient
from github_client import GitHubClient
from mapper import IssueMapper
from models import JiraIssue, MigrationResult
from config import Config
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich import print as rprint


class MigrationService:
    """Service for migrating Jira issues to GitHub"""

    def __init__(self, config: Config, failed_issues_file: str = None):
        self.config = config
        self.failed_issues_file = failed_issues_file
        self.jira_client = JiraClient(config)
        self.github_client = GitHubClient(config)
        self.mapper = IssueMapper(config)
        self.console = Console()
    
    def migrate_issues_by_keys(self, issue_keys: List[str]) -> List[MigrationResult]:
        """Migrate specific Jira issues by their keys"""
        rprint(f"[bold blue]Starting migration of {len(issue_keys)} issues...[/bold blue]")
        
        # Fetch Jira issues
        jira_issues = self.jira_client.get_issues_by_keys(issue_keys)
        
        if not jira_issues:
            rprint("[bold red]No valid Jira issues found![/bold red]")
            return []
        
        return self._migrate_issues(jira_issues, self.failed_issues_file)
    
    def migrate_issues_by_jql(self, jql: str, max_results: int = 50, start_at: int = 0) -> List[MigrationResult]:
        """Migrate Jira issues found by JQL query"""
        rprint(f"[bold blue]Searching for issues with JQL: {jql}[/bold blue]")
        if start_at > 0:
            rprint(f"[blue]Starting at offset: {start_at}[/blue]")

        # Search for issues
        jira_issues = self.jira_client.search_issues(jql, max_results, start_at)
        
        if not jira_issues:
            rprint("[bold red]No issues found matching the JQL query![/bold red]")
            return []
        
        rprint(f"[green]Found {len(jira_issues)} issues to migrate[/green]")
        return self._migrate_issues(jira_issues, self.failed_issues_file)
    
    def migrate_project_issues(self, project_key: str, status: str = None) -> List[MigrationResult]:
        """Migrate all issues from a Jira project"""
        rprint(f"[bold blue]Migrating issues from project: {project_key}[/bold blue]")
        if status:
            rprint(f"[blue]Filtering by status: {status}[/blue]")
        
        # Get project issues
        jira_issues = self.jira_client.get_project_issues(project_key, status)
        
        if not jira_issues:
            rprint("[bold red]No issues found in the project![/bold red]")
            return []
        
        rprint(f"[green]Found {len(jira_issues)} issues to migrate[/green]")
        return self._migrate_issues(jira_issues, self.failed_issues_file)
    
    def _migrate_issues(self, jira_issues: List[JiraIssue], failed_issues_file: str = None) -> List[MigrationResult]:
        """Internal method to migrate a list of Jira issues"""
        results = []

        # Create required labels
        self._ensure_labels_exist(jira_issues)

        # Migrate issues with progress bar
        with Progress() as progress:
            task = progress.add_task("[green]Migrating issues...", total=len(jira_issues))

            for jira_issue in jira_issues:
                progress.update(task, description=f"[green]Migrating {jira_issue.key}...")

                # Get comments if requested
                comments = []
                if self.config.include_comments:
                    comments = self.jira_client.get_issue_comments(jira_issue.key)

                # Get attachments if requested
                attachments = []
                if self.config.include_attachments:
                    attachments = self.jira_client.get_issue_attachments(jira_issue.key)

                # Map to GitHub issue
                github_issue = self.mapper.map_jira_to_github(jira_issue, comments, attachments)

                # Create GitHub issue
                result = self.github_client.create_issue(github_issue)
                result.jira_key = jira_issue.key
                results.append(result)

                # Show result
                if result.success:
                    rprint(f"[green]✓ {jira_issue.key} -> GitHub #{result.github_issue_number}[/green]")
                else:
                    rprint(f"[red]✗ {jira_issue.key}: {result.error_message}[/red]")

                progress.advance(task)

        # Show summary
        self._show_migration_summary(results, failed_issues_file)

        return results
    
    def _ensure_labels_exist(self, jira_issues: List[JiraIssue]):
        """Ensure all required labels exist in the GitHub repository"""
        if self.config.dry_run:
            return
        
        rprint("[blue]Ensuring required labels exist...[/blue]")
        
        existing_labels = set(self.github_client.get_repo_labels())
        required_labels = set()
        
        # Collect all labels that will be used
        for jira_issue in jira_issues:
            # @TODO: this technically creates redundant mapping work since we're calling
            # map_jira_to_github() later again but its fine for now 
            github_issue = self.mapper.map_jira_to_github(jira_issue)
            required_labels.update(github_issue.labels)
        
        # Create missing labels
        missing_labels = required_labels - existing_labels
        for label in missing_labels:
            color = self._get_label_color(label)
            if self.github_client.create_label(label, color):
                rprint(f"[green]Created label: {label}[/green]")
    
    def _get_label_color(self, label: str) -> str:
        """Get appropriate color for a label"""
        color_map = {
            'priority: critical': 'ff0000',
            'priority: high': 'ff6600',
            'priority: medium': 'ffcc00',
            'priority: low': '00ff00',
            'priority: lowest': '99ff99',
            'type: bug': 'fc2929',
            'type: feature': '0052cc',
            'type: enhancement': '0052cc',
            'type: task': 'fef2c0',
            'type: epic': '3e4b9e',
            'status: todo': 'ededed',
            'status: in-progress': 'fbca04',
            'status: done': '0e8a16',
            'status: closed': '6f42c1',
            'migrated-from-jira': '8b5a2b'
        }
        
        return color_map.get(label, 'ededed')
    
    def _show_migration_summary(self, results: List[MigrationResult], failed_issues_file: str = None):
        """Show a summary of the migration results"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        table = Table(title="Migration Summary")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        total = len(results)
        success_count = len(successful)
        failure_count = len(failed)

        if success_count > 0:
            table.add_row(
                "[green]Successful[/green]",
                str(success_count),
                f"{(success_count/total)*100:.1f}%" if total > 0 else "0%"
            )
        if failure_count > 0:
            table.add_row(
                "[red]Failed[/red]",
                str(failure_count),
                f"{(failure_count/total)*100:.1f}%" if total > 0 else "0%"
            )
        table.add_row(
            "[bold]Total[/bold]",
            str(total),
            "100%"
        )

        self.console.print(table)

        # Show failed issues
        if failed:
            rprint("\n[bold red]Failed Issues:[/bold red]")
            for result in failed:
                rprint(f"  • {result.jira_key}: {result.error_message}")

            # Write failed issues to file if specified
            if failed_issues_file:
                self._write_failed_issues_report(failed, failed_issues_file)

        # Show successful issues
        if successful and not self.config.dry_run:
            rprint("\n[bold green]Successfully Created Issues:[/bold green]")
            for result in successful[:5]:  # Show first 5
                rprint(f"  • {result.jira_key} -> {result.github_url}")
            if len(successful) > 5:
                rprint(f"  ... and {len(successful) - 5} more")

    def _write_failed_issues_report(self, failed_results: List[MigrationResult], output_file: str):
        """Write detailed failed issues report to JSON file"""
        import json
        from datetime import datetime

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_failed": len(failed_results),
            "failed_issues": []
        }

        for result in failed_results:
            issue_detail = {
                "jira_key": result.jira_key,
                "error_message": result.error_message,
                "timestamp": datetime.now().isoformat()
            }
            report["failed_issues"].append(issue_detail)

        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            rprint(f"\n[yellow]📄 Failed issues report written to: {output_file}[/yellow]")
        except Exception as e:
            rprint(f"\n[red]Error writing failed issues report: {e}[/red]")
    
    def preview_migration(self, issue_keys: List[str], show_full: bool = False) -> None:
        """Preview what would be migrated without actually creating issues"""
        rprint("[bold blue]Preview Mode - No issues will be created[/bold blue]")
        
        jira_issues = self.jira_client.get_issues_by_keys(issue_keys)
        
        if not jira_issues:
            rprint("[bold red]No valid Jira issues found![/bold red]")
            return
        
        for jira_issue in jira_issues:
            comments = []
            if self.config.include_comments:
                comments = self.jira_client.get_issue_comments(jira_issue.key)
            
            attachments = []
            if self.config.include_attachments:
                attachments = self.jira_client.get_issue_attachments(jira_issue.key)
            
            github_issue = self.mapper.map_jira_to_github(jira_issue, comments, attachments)
            
            rprint(f"\n[bold cyan]Jira Issue: {jira_issue.key}[/bold cyan]")
            rprint(f"[yellow]Title:[/yellow] {github_issue.title}")
            rprint(f"[yellow]Labels:[/yellow] {', '.join(github_issue.labels)}")
            if github_issue.assignees:
                rprint(f"[yellow]Assignees:[/yellow] {', '.join(github_issue.assignees)}")
            rprint(f"[yellow]Body Length:[/yellow] {len(github_issue.body)} characters")
            
            # Show body content
            if show_full:
                rprint(f"[yellow]Full Body:[/yellow]\n{github_issue.body}")
            else:
                body_preview = github_issue.body[:500] + "..." if len(github_issue.body) > 500 else github_issue.body
                rprint(f"[yellow]Body Preview:[/yellow]\n{body_preview}")
            
            if comments:
                rprint(f"[yellow]Comments:[/yellow] {len(comments)} comments to be included")
            
            if attachments:
                rprint(f"[yellow]Attachments:[/yellow] {len(attachments)} files to be included")
