from typing import List, Dict, Any, Optional
from mapper import IssueMapper
from user_mapping import UserMappingService
from label_manager import LabelManager
from models import JiraIssue
from enhanced_models import EnhancedGitHubIssue, UserMappingStats, LabelEnhancementStats
from config import Config
import re


class EnhancedIssueMapper(IssueMapper):
    """Enhanced issue mapper with user mapping, label enhancement, and state migration"""
    
    def __init__(self, config: Config, user_mapping: UserMappingService = None, 
                 label_manager: LabelManager = None, migrate_closed: bool = False):
        super().__init__(config)
        self.user_mapping = user_mapping
        self.label_manager = label_manager
        self.migrate_closed = migrate_closed
        
        # Statistics tracking
        self.user_stats = UserMappingStats()
        self.label_stats = LabelEnhancementStats()
    
    def map_jira_to_github(self, jira_issue: JiraIssue, comments: List[Dict] = None, 
                          attachments: List[Dict] = None) -> EnhancedGitHubIssue:
        """Convert a Jira issue to an enhanced GitHub issue with all enhancements"""
        
        # Start with base mapping from parent class
        base_issue = super().map_jira_to_github(jira_issue, comments, attachments)
        
        # Create enhanced issue
        enhanced_issue = EnhancedGitHubIssue(
            title=base_issue.title,
            body="",  # We'll rebuild this with enhancements
            labels=[],  # We'll rebuild this with enhancements
            assignees=[],  # We'll rebuild this with user mapping
            milestone=base_issue.milestone,
            state=self._determine_github_state(jira_issue),
            original_assignee=jira_issue.assignee,
            mapped_assignee=None
        )
        
        # Apply user mapping for assignees
        enhanced_issue.assignees = self._map_assignees_with_stats(jira_issue)
        if enhanced_issue.assignees:
            enhanced_issue.mapped_assignee = enhanced_issue.assignees[0]
        
        # Apply enhanced label generation
        enhanced_issue.labels = self._generate_enhanced_labels_with_stats(jira_issue)
        
        # Create enhanced body with user mapping in comments
        enhanced_issue.body = self._create_enhanced_issue_body(jira_issue, comments or [], attachments or [])
        
        return enhanced_issue
    
    def _determine_github_state(self, jira_issue: JiraIssue) -> str:
        """Determine GitHub issue state based on Jira status"""
        if not self.migrate_closed:
            return "open"
        
        # Common closed statuses in Jira
        closed_statuses = {
            'done', 'closed', 'resolved', 'complete', 'completed',
            'fixed', 'won\'t fix', 'wont fix', 'duplicate', 'invalid',
            'cannot reproduce', 'rejected', 'abandoned'
        }
        
        status_lower = jira_issue.status.lower()
        return "closed" if status_lower in closed_statuses else "open"
    
    def _map_assignees_with_stats(self, jira_issue: JiraIssue) -> List[str]:
        """Map Jira assignees to GitHub usernames with statistics tracking"""
        assignees = []
        
        if jira_issue.assignee and self.user_mapping and self.user_mapping.is_mapping_loaded():
            github_user = self.user_mapping.jira_user_to_github_username(jira_issue.assignee)
            
            if github_user:
                assignees.append(github_user)
                self.user_stats.add_user_encounter(True, "assignee")
            else:
                self.user_stats.add_user_encounter(False, "assignee")
        
        return assignees
    
    def _generate_enhanced_labels_with_stats(self, jira_issue: JiraIssue) -> List[str]:
        """Generate enhanced labels with statistics tracking"""
        self.label_stats.original_labels = len(jira_issue.labels)
        
        if self.label_manager:
            labels = self.label_manager.generate_enhanced_labels(jira_issue)
            
            # Count enhancements by category
            for label in labels:
                if label.startswith('type:'):
                    self.label_stats.type_labels_added += 1
                elif label.startswith('priority:'):
                    self.label_stats.priority_labels_added += 1
                elif label.startswith('status:'):
                    self.label_stats.status_labels_added += 1
                elif label.startswith('component:'):
                    self.label_stats.component_labels_added += 1
            
            # Ensure labels exist if auto-creation is enabled
            creation_stats = self.label_manager.ensure_labels_exist(labels)
            self.label_stats.labels_auto_created.extend(creation_stats.labels_auto_created)
            
            return labels
        else:
            # Fallback to parent class behavior
            return super()._map_labels(jira_issue)
    
    def _create_enhanced_issue_body(self, jira_issue: JiraIssue, comments: List[Dict], 
                                  attachments: List[Dict]) -> str:
        """Create enhanced issue body with improved user attribution"""
        body_parts = []
        
        # Header with Jira link
        jira_url = f"{self.config.jira_server_url}/browse/{jira_issue.key}"
        body_parts.append(f"**Migrated from Jira:** [{jira_issue.key}]({jira_url})")
        body_parts.append("")
        
        # Description
        if jira_issue.description:
            body_parts.append("## Description")
            converted_description = self._convert_jira_markup(jira_issue.description)
            # Replace image references with attachment links if available
            converted_description = self._replace_image_references(converted_description, attachments)
            body_parts.append(converted_description)
            body_parts.append("")
        
        # Attachments section (same as parent)
        if attachments:
            body_parts.append("## Attachments")
            body_parts.append("⚠️ **Note**: Jira attachments are not automatically migrated. You'll need to download them manually from Jira and re-upload to GitHub if needed.")
            body_parts.append("")
            for attachment in attachments:
                filename = attachment.get('filename', 'Unknown file')
                download_url = attachment.get('content', '#')
                size = attachment.get('size', 0)
                
                # Format file size
                if size > 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} bytes"
                
                # Check if it's an image
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
                    body_parts.append(f"📷 **{filename}** ({size_str})")
                    body_parts.append(f"   - [Download from Jira]({download_url}) (requires Jira login)")
                else:
                    body_parts.append(f"📎 **{filename}** ({size_str})")
                    body_parts.append(f"   - [Download from Jira]({download_url}) (requires Jira login)")
                body_parts.append("")
        
        # Enhanced metadata section
        body_parts.append("## Jira Details")
        body_parts.append(f"- **Issue Type:** {jira_issue.issue_type}")
        body_parts.append(f"- **Priority:** {jira_issue.priority}")
        body_parts.append(f"- **Status:** {jira_issue.status}")
        # Enhanced reporter with GitHub mapping
        if self.user_mapping and self.user_mapping.is_mapping_loaded():
            github_mention = self.user_mapping.jira_user_to_github_mention(jira_issue.reporter)
            if github_mention and github_mention != jira_issue.reporter:
                body_parts.append(f"- **Reporter:** {jira_issue.reporter} ({github_mention})")
            else:
                body_parts.append(f"- **Reporter:** {jira_issue.reporter}")
        else:
            body_parts.append(f"- **Reporter:** {jira_issue.reporter}")
        
        if jira_issue.assignee:
            # Enhanced assignee with GitHub mapping
            if self.user_mapping and self.user_mapping.is_mapping_loaded():
                github_mention = self.user_mapping.jira_user_to_github_mention(jira_issue.assignee)
                if github_mention:
                    body_parts.append(f"- **Assignee:** {jira_issue.assignee} ({github_mention})")
                else:
                    body_parts.append(f"- **Assignee:** {jira_issue.assignee}")
            else:
                body_parts.append(f"- **Assignee:** {jira_issue.assignee}")
        
        body_parts.append(f"- **Created:** {jira_issue.created.strftime('%Y-%m-%d %H:%M:%S')}")
        body_parts.append(f"- **Updated:** {jira_issue.updated.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if jira_issue.components:
            body_parts.append(f"- **Components:** {', '.join(jira_issue.components)}")
        
        body_parts.append("")
        
        # Enhanced comments with user mapping
        if comments and self.config.include_comments:
            body_parts.append("## Comments")
            comments_enhanced = 0
            users_mentioned = 0
            
            for comment in comments:
                author = comment.get('author', {}).get('displayName', 'Unknown')
                created = comment.get('created', '')
                if created:
                    # Parse the date
                    try:
                        from datetime import datetime
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                comment_body = comment.get('body', '')
                converted_body = self._convert_jira_markup(comment_body)
                
                # Enhanced comment header with user mapping
                if self.user_mapping and self.user_mapping.is_mapping_loaded():
                    enhanced_header = self.user_mapping.enhance_comment_attribution(author, created)
                    if "@" in enhanced_header:  # User was mapped
                        users_mentioned += 1
                    comments_enhanced += 1
                    body_parts.append(enhanced_header)
                else:
                    body_parts.append(f"### Comment by {author} ({created})")
                
                body_parts.append(converted_body)
                body_parts.append("")
            
            # Update statistics
            self.user_stats.comments_enhanced = comments_enhanced
            self.user_stats.new_mentions_created = users_mentioned
        
        return "\n".join(body_parts)
    
    def get_user_mapping_stats(self) -> UserMappingStats:
        """Get user mapping statistics from this mapping session"""
        return self.user_stats
    
    def get_label_enhancement_stats(self) -> LabelEnhancementStats:
        """Get label enhancement statistics from this mapping session"""
        return self.label_stats
    
    def reset_stats(self):
        """Reset statistics for a new mapping session"""
        self.user_stats = UserMappingStats()
        self.label_stats = LabelEnhancementStats()