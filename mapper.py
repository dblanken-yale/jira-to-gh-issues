from typing import List, Dict, Any, Optional
from models import JiraIssue, GitHubIssue
from config import Config
import re


class IssueMapper:
    """Maps Jira issues to GitHub issues"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def map_jira_to_github(self, jira_issue: JiraIssue, comments: List[Dict] = None, attachments: List[Dict] = None) -> GitHubIssue:
        """Convert a Jira issue to a GitHub issue"""
        
        # Create the title
        title = f"[{jira_issue.key}] {jira_issue.summary}"
        
        # Create the body
        body = self._create_issue_body(jira_issue, comments or [], attachments or [])
        
        # Map labels
        labels = self._map_labels(jira_issue)
        
        # @TODO: This would need to fetch the actual GitHub usernames.
        # For now, we just skip assignee mapping.
        # assignees = self._map_assignees(jira_issue)
        assignees = []
        
        return GitHubIssue(
            title=title,
            body=body,
            labels=labels,
            assignees=assignees
        )
    
    def _create_issue_body(self, jira_issue: JiraIssue, comments: List[Dict], attachments: List[Dict]) -> str:
        """Create the GitHub issue body from Jira issue data"""
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
        
        # Attachments section
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
                    body_parts.append(f"� **{filename}** ({size_str})")
                    body_parts.append(f"   - [Download from Jira]({download_url}) (requires Jira login)")
                body_parts.append("")
        
        # Metadata
        body_parts.append("## Jira Details")
        body_parts.append(f"- **Issue Type:** {jira_issue.issue_type}")
        body_parts.append(f"- **Priority:** {jira_issue.priority}")
        body_parts.append(f"- **Status:** {jira_issue.status}")
        body_parts.append(f"- **Reporter:** {jira_issue.reporter}")
        if jira_issue.assignee:
            body_parts.append(f"- **Assignee:** {jira_issue.assignee}")
        body_parts.append(f"- **Created:** {jira_issue.created.strftime('%Y-%m-%d %H:%M:%S')}")
        body_parts.append(f"- **Updated:** {jira_issue.updated.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if jira_issue.components:
            body_parts.append(f"- **Components:** {', '.join(jira_issue.components)}")
        
        body_parts.append("")
        
        # Comments
        if comments and self.config.include_comments:
            body_parts.append("## Comments")
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
                
                body_parts.append(f"### Comment by {author} ({created})")
                body_parts.append(converted_body)
                body_parts.append("")
        
        return "\n".join(body_parts)
    
    def _convert_jira_markup(self, text: str) -> str:
        """Convert Jira markup to GitHub markdown"""
        if not text:
            return ""
        
        # Convert Jira bold to Markdown bold
        text = re.sub(r'\*([^*]+)\*', r'**\1**', text)
        
        # Convert Jira italic to Markdown italic
        text = re.sub(r'_([^_]+)_', r'*\1*', text)
        
        # Convert Jira monospace to Markdown code
        text = re.sub(r'\{\{([^}]+)\}\}', r'`\1`', text)
        
        # Convert Jira code blocks
        text = re.sub(r'\{code(?::([^}]*))?\}(.*?)\{code\}', r'```\1\n\2\n```', text, flags=re.DOTALL)
        
        # Convert Jira quotes
        text = re.sub(r'\{quote\}(.*?)\{quote\}', r'> \1', text, flags=re.DOTALL)
        
        # Convert Jira images using a single comprehensive pattern
        def convert_jira_image(match):
            """Convert a single Jira image match to markdown"""
            full_match = match.group(0)
            filename = match.group(1)
            
            # Extract alt text if present
            alt_match = re.search(r'alt="([^"]*)"', full_match)
            if alt_match:
                alt_text = alt_match.group(1)
                return f'![image: {alt_text}]({filename})'
            else:
                return f'![image]({filename})'
        
        # Single pattern that matches all Jira image formats
        image_pattern = r'!([^!\s]+\.[a-zA-Z0-9]+)(?:\|[^!]*)?!'
        text = re.sub(image_pattern, convert_jira_image, text)
        
        # Convert Jira links (avoid matching already converted markdown images)
        text = re.sub(r'\[([^|\]]+)\|([^\]]+)\]', r'[\1](\2)', text)
        # Only match links that are not preceded by ! (to avoid matching images)
        text = re.sub(r'(?<!\!)\[([^\]]+)\](?!\()', r'[\1](\1)', text)
        
        # Convert Jira headers
        text = re.sub(r'^h1\. ', '# ', text, flags=re.MULTILINE)
        text = re.sub(r'^h2\. ', '## ', text, flags=re.MULTILINE)
        text = re.sub(r'^h3\. ', '### ', text, flags=re.MULTILINE)
        text = re.sub(r'^h4\. ', '#### ', text, flags=re.MULTILINE)
        text = re.sub(r'^h5\. ', '##### ', text, flags=re.MULTILINE)
        text = re.sub(r'^h6\. ', '###### ', text, flags=re.MULTILINE)
        
        # Convert Jira lists
        text = re.sub(r'^\* ', '- ', text, flags=re.MULTILINE)
        text = re.sub(r'^# ', '1. ', text, flags=re.MULTILINE)
        
        return text
    
    def _replace_image_references(self, text: str, attachments: List[Dict]) -> str:
        """Replace Jira image references with manual download instructions"""
        if not attachments:
            return text
        
        # Create a mapping of filenames to URLs
        attachment_map = {}
        for attachment in attachments:
            filename = attachment.get('filename', '')
            url = attachment.get('content', '')
            if filename and url:
                attachment_map[filename] = url
        
        # Replace image references in the text with manual download instructions
        for filename, url in attachment_map.items():
            # Replace various patterns that might reference this file
            patterns = [
                rf'!\[image: [^\]]*\]\({re.escape(filename)}\)',
                rf'!\[image\]\({re.escape(filename)}\)',
                rf'!\[[^\]]*\]\({re.escape(filename)}\)'
            ]
            
            for pattern in patterns:
                # Replace with manual download instruction
                replacement = f'🖼️ **Image: {filename}** - [Download from Jira]({url}) (manual upload to GitHub required)'
                text = re.sub(pattern, replacement, text)
        
        return text
    
    def _map_labels(self, jira_issue: JiraIssue) -> List[str]:
        """Map Jira issue data to GitHub labels"""
        labels = []
        
        # Add original Jira labels directly (without prefix to keep them clean)
        for label in jira_issue.labels:
            labels.append(label.lower())
        
        # Add migration label to track migrated issues
        labels.append("migrated-from-jira")
        
        return labels
    
    # @TODO: this would need to fetch the actual GitHub usernames
    def _map_assignees(self, jira_issue: JiraIssue) -> List[str]:
        """Map Jira assignee to GitHub username"""
        # This is a simple mapping - you might want to create a more sophisticated
        # mapping system based on email addresses or a mapping file
        assignees = []
        
        if jira_issue.assignee:
            assignees.append(jira_issue.assignee.lower().replace(" ", ""))
        
        return assignees
