from typing import Dict, Any
from jira_user_client import JiraUserClient
from config import Config
from datetime import datetime
import json
import os
from rich.console import Console
from rich.table import Table
from rich import print as rprint


class UserDiscoveryService:
    """Service for discovering and generating user mapping files from Jira projects"""
    
    def __init__(self, config: Config):
        self.config = config
        self.user_client = JiraUserClient(config)
        self.console = Console()
    
    def generate_user_mapping_template(self, project_key: str, output_file: str = None) -> str:
        """
        Generate a user mapping template file for a Jira project.
        Returns the path to the generated file.
        """
        if not output_file:
            output_file = f"user-mapping-{project_key.lower()}.json"
        
        rprint(f"[bold blue]🔍 Generating user mapping template for project {project_key}[/bold blue]")
        
        # Discover all users
        users = self.user_client.get_comprehensive_project_users(project_key)
        
        if not users:
            rprint("[bold red]❌ No users found for this project[/bold red]")
            return None
        
        # Sort users by activity level (most active first)
        sorted_users = sorted(
            users.items(), 
            key=lambda x: x[1].get('issue_activity_count', 0), 
            reverse=True
        )
        
        # Generate the mapping template
        mapping_data = {
            "_metadata": {
                "project": project_key,
                "generated": datetime.now().isoformat(),
                "jira_server": self.config.jira_server_url,
                "total_users": len(users),
                "sources_used": self._get_unique_sources(users),
                "instructions": [
                    "Fill in the 'github_username' field for each user you want to map",
                    "Users are sorted by activity level (most active first)",
                    "You can delete entries for users you don't want to migrate",
                    "Leave 'github_username' as null for users you want to skip"
                ]
            },
            "user_mapping": {}
        }
        
        # Build user mapping entries
        for user_id, user_data in sorted_users:
            # Use email as key if available, otherwise display name, otherwise account ID
            key = user_data.get('email_address') or user_data.get('display_name') or user_id
            
            mapping_data["user_mapping"][key] = {
                "display_name": user_data.get('display_name'),
                "jira_account_id": user_id,
                "email_address": user_data.get('email_address'),
                "roles": user_data.get('roles', []),
                "sources": user_data.get('sources', []),
                "active": user_data.get('active', True),
                "issue_activity_count": user_data.get('issue_activity_count', 0),
                "github_username": None,  # This is what users need to fill in
                "notes": ""  # Space for user notes
            }
        
        # Write to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, indent=2, ensure_ascii=False)
            
            rprint(f"[bold green]✅ Generated user mapping template: {output_file}[/bold green]")
            
            # Show summary
            self._display_user_summary(users, project_key)
            self._show_next_steps(output_file)
            
            return output_file
            
        except Exception as e:
            rprint(f"[bold red]❌ Error writing mapping file: {e}[/bold red]")
            return None
    
    def validate_mapping_file(self, mapping_file: str) -> bool:
        """Validate a user mapping file format"""
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            if "_metadata" not in data or "user_mapping" not in data:
                rprint(f"[bold red]❌ Invalid mapping file structure in {mapping_file}[/bold red]")
                return False
            
            # Check for any mapped users
            mapped_users = [
                user for user, info in data["user_mapping"].items() 
                if info.get("github_username")
            ]
            
            if not mapped_users:
                rprint(f"[bold yellow]⚠️  No GitHub usernames mapped in {mapping_file}[/bold yellow]")
                rprint("[yellow]Make sure to fill in 'github_username' fields before using for migration[/yellow]")
                return False
            
            rprint(f"[bold green]✅ Mapping file is valid with {len(mapped_users)} mapped users[/bold green]")
            return True
            
        except FileNotFoundError:
            rprint(f"[bold red]❌ Mapping file not found: {mapping_file}[/bold red]")
            return False
        except json.JSONDecodeError as e:
            rprint(f"[bold red]❌ Invalid JSON in mapping file: {e}[/bold red]")
            return False
        except Exception as e:
            rprint(f"[bold red]❌ Error validating mapping file: {e}[/bold red]")
            return False
    
    def show_mapping_stats(self, mapping_file: str):
        """Display statistics about a mapping file"""
        if not os.path.exists(mapping_file):
            rprint(f"[bold red]❌ Mapping file not found: {mapping_file}[/bold red]")
            return
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get("_metadata", {})
            user_mapping = data.get("user_mapping", {})
            
            # Count mapped vs unmapped users
            mapped_count = sum(1 for info in user_mapping.values() if info.get("github_username"))
            total_count = len(user_mapping)
            unmapped_count = total_count - mapped_count
            
            # Create summary table
            table = Table(title=f"User Mapping Statistics: {mapping_file}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Project", metadata.get("project", "Unknown"))
            table.add_row("Generated", metadata.get("generated", "Unknown")[:19])  # Remove microseconds
            table.add_row("Total Users", str(total_count))
            table.add_row("Mapped Users", str(mapped_count))
            table.add_row("Unmapped Users", str(unmapped_count))
            table.add_row("Completion", f"{(mapped_count/total_count)*100:.1f}%" if total_count > 0 else "0%")
            
            self.console.print(table)
            
            if unmapped_count > 0:
                rprint(f"\n[yellow]💡 {unmapped_count} users still need GitHub usernames assigned[/yellow]")
            
            # Show top active users if any are unmapped
            unmapped_active = [
                (user, info) for user, info in user_mapping.items()
                if not info.get("github_username") and info.get("issue_activity_count", 0) > 0
            ]
            
            if unmapped_active:
                unmapped_active.sort(key=lambda x: x[1].get("issue_activity_count", 0), reverse=True)
                rprint("\n[bold]🔥 Most active unmapped users:[/bold]")
                for user, info in unmapped_active[:5]:  # Top 5
                    activity = info.get("issue_activity_count", 0)
                    display_name = info.get("display_name", user)
                    rprint(f"   • {display_name}: {activity} issue interactions")
            
        except Exception as e:
            rprint(f"[bold red]❌ Error reading mapping file: {e}[/bold red]")
    
    def _get_unique_sources(self, users: Dict[str, Dict[str, Any]]) -> list:
        """Get all unique sources used across all users"""
        sources = set()
        for user_data in users.values():
            sources.update(user_data.get('sources', []))
        return sorted(list(sources))
    
    def _display_user_summary(self, users: Dict[str, Dict[str, Any]], project_key: str):
        """Display a summary table of discovered users"""
        # Count by source
        source_counts = {}
        total_activity = 0
        
        for user_data in users.values():
            for source in user_data.get('sources', []):
                source_counts[source] = source_counts.get(source, 0) + 1
            total_activity += user_data.get('issue_activity_count', 0)
        
        table = Table(title=f"User Discovery Summary - {project_key}")
        table.add_column("Source", style="cyan")
        table.add_column("Users Found", style="green")
        
        for source, count in sorted(source_counts.items()):
            table.add_row(source.replace('_', ' ').title(), str(count))
        
        table.add_row("[bold]Total Unique Users[/bold]", f"[bold]{len(users)}[/bold]")
        table.add_row("Total Issue Interactions", str(total_activity))
        
        self.console.print(table)
    
    def _show_next_steps(self, mapping_file: str):
        """Show next steps after generating mapping file"""
        rprint(f"\n[bold]📋 Next Steps:[/bold]")
        rprint(f"1. Edit the file: [cyan]{mapping_file}[/cyan]")
        rprint(f"2. Fill in GitHub usernames for users you want to migrate")
        rprint(f"3. Validate your mapping: [cyan]./run.sh validate-user-mapping {mapping_file}[/cyan]")
        rprint(f"4. Use in migration: [cyan]./run.sh --user-mapping-file={mapping_file} migrate ISSUE-123[/cyan]")
        rprint(f"\n[dim]💡 Tip: Users are sorted by activity level - focus on the most active users first![/dim]")