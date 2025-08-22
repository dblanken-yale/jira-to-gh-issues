from typing import Dict, Optional, List
import json
import os
from rich import print as rprint


class UserMappingService:
    """Service for loading and using user mapping files during migration"""
    
    def __init__(self, mapping_file: str = None):
        self.mapping_file = mapping_file
        self.mapping_data = {}
        self.jira_to_github = {}
        self.github_mentions = {}
        
        if mapping_file and os.path.exists(mapping_file):
            self._load_mapping_file()
    
    def _load_mapping_file(self):
        """Load and parse the user mapping file"""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.mapping_data = data
            user_mapping = data.get("user_mapping", {})
            
            # Build lookup dictionaries for fast access
            for jira_identifier, user_info in user_mapping.items():
                github_username = user_info.get("github_username")
                if github_username:
                    # Create mappings for multiple Jira identifiers
                    display_name = user_info.get("display_name")
                    email = user_info.get("email_address")
                    account_id = user_info.get("jira_account_id")
                    
                    # Map all possible Jira identifiers to GitHub username
                    self.jira_to_github[jira_identifier] = github_username
                    
                    if display_name:
                        self.jira_to_github[display_name] = github_username
                    if email:
                        self.jira_to_github[email] = github_username
                    if account_id:
                        self.jira_to_github[account_id] = github_username
                    
                    # Create GitHub mention mapping
                    self.github_mentions[jira_identifier] = f"@{github_username}"
                    if display_name:
                        self.github_mentions[display_name] = f"@{github_username}"
                    if email:
                        self.github_mentions[email] = f"@{github_username}"
                    if account_id:
                        self.github_mentions[account_id] = f"@{github_username}"
            
            mapped_count = len([u for u in user_mapping.values() if u.get("github_username")])
            rprint(f"[green]✅ Loaded user mapping with {mapped_count} mapped users[/green]")
            
        except Exception as e:
            rprint(f"[red]❌ Error loading user mapping file {self.mapping_file}: {e}[/red]")
            self.mapping_data = {}
            self.jira_to_github = {}
            self.github_mentions = {}
    
    def is_mapping_loaded(self) -> bool:
        """Check if user mapping is loaded and has mappings"""
        return bool(self.jira_to_github)
    
    def jira_user_to_github_username(self, jira_identifier: str) -> Optional[str]:
        """
        Convert a Jira user identifier to GitHub username.
        
        Args:
            jira_identifier: Can be display name, email, or account ID
        
        Returns:
            GitHub username if mapped, None otherwise
        """
        if not jira_identifier:
            return None
        
        return self.jira_to_github.get(jira_identifier)
    
    def jira_user_to_github_mention(self, jira_identifier: str) -> Optional[str]:
        """
        Convert a Jira user identifier to GitHub @mention.
        
        Args:
            jira_identifier: Can be display name, email, or account ID
        
        Returns:
            GitHub @mention if mapped, None otherwise
        """
        if not jira_identifier:
            return None
        
        return self.github_mentions.get(jira_identifier)
    
    def get_mapped_assignees(self, jira_assignee: str) -> List[str]:
        """
        Get GitHub assignee list for a Jira assignee.
        
        Args:
            jira_assignee: Jira user identifier
        
        Returns:
            List of GitHub usernames (empty if no mapping)
        """
        github_user = self.jira_user_to_github_username(jira_assignee)
        return [github_user] if github_user else []
    
    def enhance_comment_attribution(self, comment_author: str, comment_date: str) -> str:
        """
        Create enhanced comment attribution with GitHub user mapping.
        
        Args:
            comment_author: Original Jira comment author
            comment_date: Comment creation date
        
        Returns:
            Enhanced comment header with attribution
        """
        github_user = self.jira_user_to_github_mention(comment_author)
        
        if github_user:
            return f"### Comment by {github_user} (originally {comment_author}) on {comment_date}"
        else:
            return f"### Comment by {comment_author} on {comment_date}"
    
    def get_mapping_stats(self) -> Dict[str, any]:
        """Get statistics about the loaded mapping"""
        if not self.mapping_data:
            return {"loaded": False}
        
        user_mapping = self.mapping_data.get("user_mapping", {})
        total_users = len(user_mapping)
        mapped_users = len([u for u in user_mapping.values() if u.get("github_username")])
        
        return {
            "loaded": True,
            "mapping_file": self.mapping_file,
            "total_users": total_users,
            "mapped_users": mapped_users,
            "unmapped_users": total_users - mapped_users,
            "completion_rate": (mapped_users / total_users * 100) if total_users > 0 else 0,
            "project": self.mapping_data.get("_metadata", {}).get("project"),
            "generated": self.mapping_data.get("_metadata", {}).get("generated")
        }
    
    def get_unmapped_active_users(self, limit: int = 10) -> List[Dict[str, any]]:
        """Get list of unmapped users sorted by activity"""
        if not self.mapping_data:
            return []
        
        user_mapping = self.mapping_data.get("user_mapping", {})
        unmapped = []
        
        for jira_id, user_info in user_mapping.items():
            if not user_info.get("github_username"):
                unmapped.append({
                    "jira_identifier": jira_id,
                    "display_name": user_info.get("display_name"),
                    "activity_count": user_info.get("issue_activity_count", 0),
                    "roles": user_info.get("roles", []),
                    "active": user_info.get("active", True)
                })
        
        # Sort by activity count (descending)
        unmapped.sort(key=lambda x: x["activity_count"], reverse=True)
        return unmapped[:limit]
    
    def suggest_github_usernames(self, jira_identifier: str) -> List[str]:
        """
        Suggest possible GitHub usernames based on Jira user info.
        
        Args:
            jira_identifier: Jira user identifier
        
        Returns:
            List of suggested GitHub usernames
        """
        if not self.mapping_data:
            return []
        
        user_mapping = self.mapping_data.get("user_mapping", {})
        user_info = user_mapping.get(jira_identifier)
        
        if not user_info:
            return []
        
        suggestions = []
        display_name = user_info.get("display_name", "")
        email = user_info.get("email_address", "")
        
        # Create suggestions based on display name
        if display_name:
            # "John Doe" -> ["johndoe", "john-doe", "jdoe"]
            name_parts = display_name.lower().split()
            if len(name_parts) >= 2:
                suggestions.append(''.join(name_parts))  # johndoe
                suggestions.append('-'.join(name_parts))  # john-doe
                suggestions.append(name_parts[0] + name_parts[-1][0])  # johnd
        
        # Create suggestions based on email
        if email and '@' in email:
            email_username = email.split('@')[0].lower()
            suggestions.append(email_username)
            # Remove dots/underscores for GitHub format
            suggestions.append(email_username.replace('.', ''))
            suggestions.append(email_username.replace('_', '-'))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Return top 5 suggestions