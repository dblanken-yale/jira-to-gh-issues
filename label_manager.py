from typing import List, Dict, Set, Any
from github_client import GitHubClient
from models import JiraIssue
from enhanced_models import LabelEnhancementStats
from rich import print as rprint
import re


class LabelManager:
    """Manages label creation and enhancement for GitHub issues"""
    
    def __init__(self, github_client: GitHubClient, auto_create: bool = False):
        self.github_client = github_client
        self.auto_create = auto_create
        self.existing_labels = set()
        self.created_labels = set()
        self.label_colors = self._get_default_label_colors()
        
        # Load existing labels from repository
        self._load_existing_labels()
    
    def _load_existing_labels(self):
        """Load existing labels from the GitHub repository"""
        try:
            existing = self.github_client.get_repo_labels()
            self.existing_labels = set(label.lower() for label in existing)
            rprint(f"[dim]📋 Loaded {len(self.existing_labels)} existing labels from repository[/dim]")
        except Exception as e:
            rprint(f"[yellow]⚠️  Could not load existing labels: {e}[/yellow]")
            self.existing_labels = set()
    
    def _get_default_label_colors(self) -> Dict[str, str]:
        """Get default colors for different label types"""
        return {
            # Issue types
            'type:bug': 'd73a49',
            'type:feature': 'a2eeef', 
            'type:enhancement': 'a2eeef',
            'type:task': '0075ca',
            'type:story': '7057ff',
            'type:epic': '6f42c1',
            'type:subtask': 'c5def5',
            'type:improvement': 'a2eeef',
            'type:new-feature': 'a2eeef',
            
            # Priorities
            'priority:blocker': 'd93f0b',
            'priority:critical': 'e99695',
            'priority:high': 'f9d0c4', 
            'priority:highest': 'b60205',
            'priority:medium': 'fbca04',
            'priority:low': 'd4c5f9',
            'priority:lowest': 'c2e0c6',
            
            # Status
            'status:todo': 'ededed',
            'status:in-progress': 'fbca04',
            'status:done': '0e8a16',
            'status:closed': '6f42c1',
            'status:open': '28a745',
            'status:reopened': 'e99695',
            'status:resolved': '0e8a16',
            'status:wont-fix': '6f42c1',
            
            # Components (generic colors)
            'component:frontend': '5319e7',
            'component:backend': '1d76db',
            'component:api': '0052cc',
            'component:database': '5319e7',
            'component:ui': 'f9d0c4',
            'component:ux': 'f9d0c4',
            
            # Migration specific
            'migrated-from-jira': '0e8a16',
            'needs-triage': 'fbca04',
            'migration-enhanced': '7057ff'
        }
    
    def generate_enhanced_labels(self, jira_issue: JiraIssue) -> List[str]:
        """
        Generate enhanced label set for a Jira issue.
        
        Returns:
            List of label names for the issue
        """
        labels = []
        
        # Start with original Jira labels
        for label in jira_issue.labels:
            labels.append(self._normalize_label(label))
        
        # Add issue type label
        issue_type = self._normalize_label(jira_issue.issue_type)
        type_label = f"type:{issue_type}"
        labels.append(type_label)
        
        # Add priority label
        priority = self._normalize_label(jira_issue.priority)
        priority_label = f"priority:{priority}"
        labels.append(priority_label)
        
        # Add status label
        status = self._normalize_label(jira_issue.status)
        status_label = f"status:{status}"
        labels.append(status_label)
        
        # Add component labels
        for component in jira_issue.components:
            component_label = f"component:{self._normalize_label(component)}"
            labels.append(component_label)
        
        # Add migration tracking label
        labels.append("migrated-from-jira")
        
        # Remove duplicates while preserving order
        unique_labels = []
        seen = set()
        for label in labels:
            if label.lower() not in seen:
                seen.add(label.lower())
                unique_labels.append(label)
        
        return unique_labels
    
    def ensure_labels_exist(self, labels: List[str]) -> LabelEnhancementStats:
        """
        Ensure all labels exist in the repository, creating them if needed.
        
        Returns:
            Statistics about label creation
        """
        stats = LabelEnhancementStats()
        labels_to_create = []
        
        for label in labels:
            label_lower = label.lower()
            
            # Check if label already exists or was created in this session
            if label_lower not in self.existing_labels and label_lower not in self.created_labels:
                labels_to_create.append(label)
        
        # Create missing labels if auto-create is enabled
        if self.auto_create and labels_to_create:
            for label in labels_to_create:
                if self._create_label(label):
                    stats.labels_auto_created.append(label)
                    self.created_labels.add(label.lower())
        
        return stats
    
    def _create_label(self, label_name: str) -> bool:
        """Create a single label in the repository"""
        try:
            # Get color for this label type
            color = self._get_label_color(label_name)
            description = self._get_label_description(label_name)
            
            success = self.github_client.create_label(label_name, color, description)
            if success:
                rprint(f"[green]✅ Created label: {label_name}[/green]")
            else:
                rprint(f"[yellow]⚠️  Failed to create label: {label_name}[/yellow]")
            
            return success
            
        except Exception as e:
            rprint(f"[red]❌ Error creating label {label_name}: {e}[/red]")
            return False
    
    def _get_label_color(self, label_name: str) -> str:
        """Get appropriate color for a label"""
        label_lower = label_name.lower()
        
        # Check for exact match first
        if label_lower in self.label_colors:
            return self.label_colors[label_lower]
        
        # Check for category matches
        if label_lower.startswith('type:'):
            return 'a2eeef'  # Light blue for types
        elif label_lower.startswith('priority:'):
            return 'fbca04'  # Yellow for priorities  
        elif label_lower.startswith('status:'):
            return '28a745'  # Green for status
        elif label_lower.startswith('component:'):
            return '5319e7'  # Purple for components
        elif 'bug' in label_lower or 'error' in label_lower:
            return 'd73a49'  # Red for bugs
        elif 'enhancement' in label_lower or 'feature' in label_lower:
            return 'a2eeef'  # Light blue for enhancements
        
        # Default color
        return 'ededed'  # Light gray
    
    def _get_label_description(self, label_name: str) -> str:
        """Get appropriate description for a label"""
        label_lower = label_name.lower()
        
        # Category-based descriptions
        if label_lower.startswith('type:'):
            return f"Issue type: {label_name.split(':', 1)[1]}"
        elif label_lower.startswith('priority:'):
            return f"Priority level: {label_name.split(':', 1)[1]}"
        elif label_lower.startswith('status:'):
            return f"Issue status: {label_name.split(':', 1)[1]}"
        elif label_lower.startswith('component:'):
            return f"Component: {label_name.split(':', 1)[1]}"
        elif label_lower == 'migrated-from-jira':
            return "Issue migrated from Jira"
        elif label_lower == 'migration-enhanced':
            return "Labels enhanced during Jira migration"
        
        # Default description
        return f"Label: {label_name}"
    
    def _normalize_label(self, text: str) -> str:
        """Normalize text for use as a GitHub label"""
        if not text:
            return ""
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        normalized = re.sub(r'[^\w\s-]', '', text.lower())
        normalized = re.sub(r'[\s_]+', '-', normalized)
        normalized = re.sub(r'-+', '-', normalized)  # Remove multiple consecutive hyphens
        normalized = normalized.strip('-')  # Remove leading/trailing hyphens
        
        return normalized
    
    def get_label_stats(self) -> Dict[str, Any]:
        """Get statistics about label management"""
        return {
            "existing_labels": len(self.existing_labels),
            "labels_created_this_session": len(self.created_labels),
            "auto_create_enabled": self.auto_create,
            "supported_categories": ["type", "priority", "status", "component"],
            "default_colors_available": len(self.label_colors)
        }
    
    def preview_labels_for_issue(self, jira_issue: JiraIssue) -> Dict[str, List[str]]:
        """Preview what labels would be generated for an issue"""
        labels = self.generate_enhanced_labels(jira_issue)
        
        categorized = {
            "original": [label for label in jira_issue.labels],
            "type": [label for label in labels if label.startswith("type:")],
            "priority": [label for label in labels if label.startswith("priority:")],
            "status": [label for label in labels if label.startswith("status:")], 
            "component": [label for label in labels if label.startswith("component:")],
            "migration": [label for label in labels if "jira" in label.lower()],
            "total": labels
        }
        
        return categorized