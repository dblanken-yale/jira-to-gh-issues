from typing import List, Optional, Dict, Any
from github import Github, Repository
from models import GitHubIssue, MigrationResult
from config import Config


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(f"{config.github_repo_owner}/{config.github_repo_name}")
    
    def create_issue(self, github_issue: GitHubIssue) -> MigrationResult:
        """Create a GitHub issue"""
        try:
            if self.config.dry_run:
                # For enhanced issues, also show state in dry run
                state_info = ""
                if hasattr(github_issue, 'state') and github_issue.state == "closed":
                    state_info = " (would be closed)"
                print(f"[DRY RUN] Would create issue: {github_issue.title}{state_info}")
                return MigrationResult(
                    jira_key="DRY_RUN",
                    success=True,
                    github_issue_number=999,
                    github_url="https://github.com/dry-run"
                )
            
            issue_data = github_issue.to_github_data()
            
            # Extract state if present (GitHub API doesn't accept state during creation)
            target_state = issue_data.pop('state', None)
            
            # Create the issue (always created as "open")
            created_issue = self.repo.create_issue(**issue_data)
            
            # If issue should be closed, close it after creation
            if target_state == "closed":
                created_issue.edit(state="closed")
            
            return MigrationResult(
                jira_key="",  # Will be set by the caller
                success=True,
                github_issue_number=created_issue.number,
                github_url=created_issue.html_url
            )
        except Exception as e:
            return MigrationResult(
                jira_key="",  # Will be set by the caller
                success=False,
                error_message=str(e)
            )
    
    def get_repo_labels(self) -> List[str]:
        """Get all labels in the repository"""
        try:
            labels = self.repo.get_labels()
            return [label.name for label in labels]
        except Exception as e:
            print(f"Error fetching repository labels: {e}")
            return []
    
    def create_label(self, name: str, color: str = "ededed", description: str = "") -> bool:
        """Create a new label in the repository"""
        try:
            if self.config.dry_run:
                print(f"[DRY RUN] Would create label: {name}")
                return True
            
            self.repo.create_label(name, color, description)
            return True
        except Exception as e:
            print(f"Error creating label {name}: {e}")
            return False
    
    def get_repo_milestones(self) -> List[str]:
        """Get all milestones in the repository"""
        try:
            milestones = self.repo.get_milestones()
            return [milestone.title for milestone in milestones]
        except Exception as e:
            print(f"Error fetching repository milestones: {e}")
            return []
    