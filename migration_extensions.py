from typing import List, Optional
from migration_service import MigrationService
from enhanced_mapper import EnhancedIssueMapper
from user_mapping import UserMappingService
from label_manager import LabelManager
from github_client import GitHubClient
from enhanced_models import EnhancedMigrationResult, UserMappingStats, LabelEnhancementStats
from models import MigrationResult
from config import Config
from rich import print as rprint
from rich.table import Table
from rich.console import Console


class EnhancedMigrationService:
    """
    Enhanced migration service that wraps the original MigrationService
    with additional functionality for user mapping, label enhancement, and state migration.
    """
    
    def __init__(self, config: Config, user_mapping_file: str = None, 
                 auto_create_labels: bool = False, migrate_closed: bool = False):
        self.config = config
        self.auto_create_labels = auto_create_labels
        self.migrate_closed = migrate_closed
        self.console = Console()
        
        # Initialize the original migration service
        self.original_service = MigrationService(config)
        
        # Initialize enhancement services
        self.user_mapping = None
        if user_mapping_file:
            self.user_mapping = UserMappingService(user_mapping_file)
        
        self.label_manager = None
        if auto_create_labels:
            github_client = GitHubClient(config)
            self.label_manager = LabelManager(github_client, auto_create=True)
        
        # Initialize enhanced mapper
        self.enhanced_mapper = EnhancedIssueMapper(
            config, 
            self.user_mapping, 
            self.label_manager,
            migrate_closed
        )
        
        # Statistics tracking
        self.total_user_stats = UserMappingStats()
        self.total_label_stats = LabelEnhancementStats()
    
    def migrate_issues_by_keys(self, issue_keys: List[str]) -> List[EnhancedMigrationResult]:
        """Migrate specific Jira issues by their keys with enhancements"""
        rprint(f"[bold blue]🚀 Starting enhanced migration of {len(issue_keys)} issues...[/bold blue]")
        
        self._show_enhancement_config()
        
        # Get Jira issues using original service's jira client
        jira_issues = self.original_service.jira_client.get_issues_by_keys(issue_keys)
        
        if not jira_issues:
            rprint("[bold red]No valid Jira issues found![/bold red]")
            return []
        
        return self._migrate_issues_enhanced(jira_issues)
    
    def migrate_issues_by_jql(self, jql: str, max_results: int = 50) -> List[EnhancedMigrationResult]:
        """Migrate Jira issues found by JQL query with enhancements"""
        rprint(f"[bold blue]🔍 Searching for issues with JQL: {jql}[/bold blue]")
        
        self._show_enhancement_config()
        
        # Search for issues using original service's jira client
        jira_issues = self.original_service.jira_client.search_issues(jql, max_results)
        
        if not jira_issues:
            rprint("[bold red]No issues found matching the JQL query![/bold red]")
            return []
        
        rprint(f"[green]Found {len(jira_issues)} issues to migrate[/green]")
        return self._migrate_issues_enhanced(jira_issues)
    
    def migrate_project_issues(self, project_key: str, status: str = None) -> List[EnhancedMigrationResult]:
        """Migrate all issues from a Jira project with enhancements"""
        rprint(f"[bold blue]📋 Migrating all issues from project {project_key}[/bold blue]")
        if status:
            rprint(f"[blue]Filtering by status: {status}[/blue]")
        
        self._show_enhancement_config()
        
        # Get project issues using original service's jira client
        jira_issues = self.original_service.jira_client.get_project_issues(project_key, status)
        
        if not jira_issues:
            rprint("[bold red]No issues found in this project![/bold red]")
            return []
        
        rprint(f"[green]Found {len(jira_issues)} issues to migrate[/green]")
        return self._migrate_issues_enhanced(jira_issues)
    
    def preview_migration(self, issue_keys: List[str], show_full: bool = False):
        """Preview enhanced migration without creating issues"""
        rprint(f"[bold cyan]🔍 Previewing enhanced migration for {len(issue_keys)} issues...[/bold cyan]")
        
        # Get issues
        jira_issues = self.original_service.jira_client.get_issues_by_keys(issue_keys)
        
        if not jira_issues:
            rprint("[bold red]No valid Jira issues found![/bold red]")
            return
        
        # Show enhancement configuration
        self._show_enhancement_config()
        
        # Preview each issue
        for jira_issue in jira_issues:
            self._preview_single_issue(jira_issue, show_full)
        
        # Show summary statistics
        self._show_preview_summary(jira_issues)
    
    def _migrate_issues_enhanced(self, jira_issues) -> List[EnhancedMigrationResult]:
        """Migrate issues using enhanced mapping and create enhanced results"""
        results = []
        
        with self.console.status("[bold green]Migrating issues...") as status:
            for i, jira_issue in enumerate(jira_issues, 1):
                status.update(f"[bold green]Migrating issue {i}/{len(jira_issues)}: {jira_issue.key}")
                
                # Reset mapper stats for this issue
                self.enhanced_mapper.reset_stats()
                
                # Get comments and attachments
                comments = []
                attachments = []
                
                if self.config.include_comments:
                    comments = self.original_service.jira_client.get_issue_comments(jira_issue.key)
                
                if self.config.include_attachments:
                    attachments = self.original_service.jira_client.get_issue_attachments(jira_issue.key)
                
                # Map to enhanced GitHub issue
                enhanced_github_issue = self.enhanced_mapper.map_jira_to_github(
                    jira_issue, comments, attachments
                )
                
                # Create the issue using original service's GitHub client
                base_result = self.original_service.github_client.create_issue(enhanced_github_issue)
                
                # Create enhanced result with additional information
                enhanced_result = EnhancedMigrationResult(
                    jira_key=jira_issue.key,
                    success=base_result.success,
                    github_issue_number=base_result.github_issue_number,
                    github_url=base_result.github_url,
                    error_message=base_result.error_message,
                    
                    # Enhancement information
                    assignee_mapped=bool(enhanced_github_issue.mapped_assignee),
                    original_assignee=enhanced_github_issue.original_assignee,
                    mapped_assignee=enhanced_github_issue.mapped_assignee,
                    labels_created=self.enhanced_mapper.get_label_enhancement_stats().labels_auto_created,
                    labels_enhanced=len(enhanced_github_issue.labels) - len(jira_issue.labels),
                    original_status=jira_issue.status,
                    github_state=enhanced_github_issue.state,
                    comments_enhanced=self.enhanced_mapper.get_user_mapping_stats().comments_enhanced,
                    users_mentioned=self.enhanced_mapper.get_user_mapping_stats().new_mentions_created
                )
                
                results.append(enhanced_result)
                
                # Update total statistics
                self._update_total_stats()
                
                # Show progress
                if enhanced_result.success:
                    enhancement_summary = enhanced_result.get_enhancement_summary()
                    if enhancement_summary != "no enhancements applied":
                        rprint(f"[green]✅ {jira_issue.key} → #{enhanced_result.github_issue_number} ({enhancement_summary})[/green]")
                    else:
                        rprint(f"[green]✅ {jira_issue.key} → #{enhanced_result.github_issue_number}[/green]")
                else:
                    rprint(f"[red]❌ {jira_issue.key}: {enhanced_result.error_message}[/red]")
        
        # Show final summary
        self._show_migration_summary(results)
        
        return results
    
    def _preview_single_issue(self, jira_issue, show_full: bool):
        """Preview a single issue's enhanced migration"""
        rprint(f"\n[bold cyan]📋 Issue: {jira_issue.key} - {jira_issue.summary}[/bold cyan]")
        
        # Reset mapper stats
        self.enhanced_mapper.reset_stats()
        
        # Get enhanced mapping
        comments = self.original_service.jira_client.get_issue_comments(jira_issue.key) if self.config.include_comments else []
        attachments = self.original_service.jira_client.get_issue_attachments(jira_issue.key) if self.config.include_attachments else []
        
        enhanced_issue = self.enhanced_mapper.map_jira_to_github(jira_issue, comments, attachments)
        
        # Show enhancements
        table = Table()
        table.add_column("Enhancement", style="cyan")
        table.add_column("Original", style="dim")
        table.add_column("Enhanced", style="green")
        
        # Assignee mapping
        original_assignee = jira_issue.assignee or "None"
        enhanced_assignees = ", ".join(enhanced_issue.assignees) if enhanced_issue.assignees else "None"
        table.add_row("Assignee", original_assignee, enhanced_assignees)
        
        # Labels
        original_labels = ", ".join(jira_issue.labels) if jira_issue.labels else "None"
        enhanced_labels = ", ".join(enhanced_issue.labels) if enhanced_issue.labels else "None"
        table.add_row("Labels", original_labels, enhanced_labels)
        
        # State
        table.add_row("State", "open (default)", enhanced_issue.state)
        
        self.console.print(table)
        
        if show_full:
            rprint("\n[dim]Enhanced Body Preview:[/dim]")
            rprint(enhanced_issue.body[:500] + "..." if len(enhanced_issue.body) > 500 else enhanced_issue.body)
    
    def _show_enhancement_config(self):
        """Show current enhancement configuration"""
        config_table = Table(title="Enhancement Configuration")
        config_table.add_column("Feature", style="cyan")
        config_table.add_column("Status", style="green")
        config_table.add_column("Details", style="dim")
        
        # User mapping
        if self.user_mapping and self.user_mapping.is_mapping_loaded():
            stats = self.user_mapping.get_mapping_stats()
            config_table.add_row(
                "User Mapping", 
                "✅ Enabled",
                f"{stats['mapped_users']}/{stats['total_users']} users mapped ({stats['completion_rate']:.1f}%)"
            )
        else:
            config_table.add_row("User Mapping", "❌ Disabled", "No mapping file provided")
        
        # Label enhancement
        if self.label_manager:
            config_table.add_row(
                "Enhanced Labels",
                "✅ Enabled", 
                f"Auto-create: {self.auto_create_labels}"
            )
        else:
            config_table.add_row("Enhanced Labels", "❌ Disabled", "")
        
        # State migration
        config_table.add_row(
            "Closed Issue Migration",
            "✅ Enabled" if self.migrate_closed else "❌ Disabled",
            "Migrating resolved issues as closed" if self.migrate_closed else ""
        )
        
        self.console.print(config_table)
        rprint("")
    
    def _update_total_stats(self):
        """Update total statistics with current mapper stats"""
        user_stats = self.enhanced_mapper.get_user_mapping_stats()
        label_stats = self.enhanced_mapper.get_label_enhancement_stats()
        
        # Merge user stats
        self.total_user_stats.total_users_encountered += user_stats.total_users_encountered
        self.total_user_stats.users_mapped += user_stats.users_mapped
        self.total_user_stats.users_unmapped += user_stats.users_unmapped
        self.total_user_stats.assignees_mapped += user_stats.assignees_mapped
        self.total_user_stats.commenters_mapped += user_stats.commenters_mapped
        self.total_user_stats.new_mentions_created += user_stats.new_mentions_created
        
        # Merge label stats
        self.total_label_stats.original_labels += label_stats.original_labels
        self.total_label_stats.type_labels_added += label_stats.type_labels_added
        self.total_label_stats.priority_labels_added += label_stats.priority_labels_added
        self.total_label_stats.status_labels_added += label_stats.status_labels_added
        self.total_label_stats.component_labels_added += label_stats.component_labels_added
        self.total_label_stats.labels_auto_created.extend(label_stats.labels_auto_created)
    
    def _show_migration_summary(self, results: List[EnhancedMigrationResult]):
        """Show comprehensive migration summary"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        rprint(f"\n[bold]📊 Migration Summary[/bold]")
        rprint(f"✅ Successful: {len(successful)}")
        rprint(f"❌ Failed: {len(failed)}")
        
        if successful:
            # Enhancement statistics
            assignees_mapped = sum(1 for r in successful if r.assignee_mapped)
            issues_closed = sum(1 for r in successful if r.github_state == "closed")
            total_labels_created = len(set(label for r in successful for label in r.labels_created))
            
            rprint(f"\n[bold]🚀 Enhancement Summary[/bold]")
            if assignees_mapped > 0:
                rprint(f"👤 {assignees_mapped} assignees mapped to GitHub users")
            
            if total_labels_created > 0:
                rprint(f"🏷️  {total_labels_created} unique labels auto-created")
            
            if issues_closed > 0:
                rprint(f"🔒 {issues_closed} issues migrated as closed")
            
            if self.total_user_stats.new_mentions_created > 0:
                rprint(f"💬 {self.total_user_stats.new_mentions_created} GitHub @mentions created in comments")
        
        # Show user mapping summary if enabled
        if self.user_mapping and self.user_mapping.is_mapping_loaded():
            rprint(f"\n[bold]👥 User Mapping Summary[/bold]")
            rprint(self.total_user_stats.get_summary())
        
        # Show label enhancement summary if enabled
        if self.label_manager:
            rprint(f"\n[bold]🏷️  Label Enhancement Summary[/bold]")
            rprint(self.total_label_stats.get_summary())
    
    def _show_preview_summary(self, jira_issues):
        """Show preview summary statistics"""
        rprint(f"\n[bold]📊 Preview Summary for {len(jira_issues)} issues[/bold]")
        
        if self.user_mapping and self.user_mapping.is_mapping_loaded():
            # Count how many assignees would be mapped
            assignable_count = sum(1 for issue in jira_issues if issue.assignee and 
                                 self.user_mapping.jira_user_to_github_username(issue.assignee))
            rprint(f"👤 {assignable_count} assignees would be mapped to GitHub users")
        
        if self.label_manager:
            # Estimate label enhancements
            total_original_labels = sum(len(issue.labels) for issue in jira_issues)
            estimated_enhanced = sum(len(self.label_manager.generate_enhanced_labels(issue)) for issue in jira_issues)
            rprint(f"🏷️  Labels would increase from {total_original_labels} to ~{estimated_enhanced}")
        
        if self.migrate_closed:
            # Count how many would be closed
            closed_statuses = {'done', 'closed', 'resolved', 'complete', 'completed', 'fixed'}
            closed_count = sum(1 for issue in jira_issues if issue.status.lower() in closed_statuses)
            rprint(f"🔒 {closed_count} issues would be migrated as closed")