from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from models import GitHubIssue, MigrationResult


@dataclass
class EnhancedGitHubIssue(GitHubIssue):
    """Enhanced GitHub issue model with additional fields for improved migration"""
    
    # Add state support for closed issue migration
    state: Optional[str] = "open"  # "open" or "closed"
    
    # Enhanced label categorization
    label_categories: Dict[str, List[str]] = field(default_factory=dict)
    
    # User mapping information
    original_assignee: Optional[str] = None
    mapped_assignee: Optional[str] = None
    
    def to_github_data(self) -> Dict[str, Any]:
        """Convert to GitHub API format with enhanced fields"""
        # Start with base data from parent class
        data = super().to_github_data()
        
        # Add state if it's not the default "open"
        if self.state and self.state != "open":
            data['state'] = self.state
        
        return data
    
    def get_labels_by_category(self, category: str) -> List[str]:
        """Get labels for a specific category (e.g., 'type', 'priority', 'status')"""
        return self.label_categories.get(category, [])
    
    def add_categorized_label(self, category: str, label: str):
        """Add a label with category tracking"""
        if category not in self.label_categories:
            self.label_categories[category] = []
        
        self.label_categories[category].append(label)
        
        # Also add to main labels list if not already there
        if label not in self.labels:
            self.labels.append(label)


@dataclass  
class EnhancedMigrationResult(MigrationResult):
    """Enhanced migration result with additional tracking information"""
    
    # User mapping results
    assignee_mapped: bool = False
    original_assignee: Optional[str] = None
    mapped_assignee: Optional[str] = None
    
    # Label enhancement results
    labels_created: List[str] = field(default_factory=list)
    labels_enhanced: int = 0
    
    # State migration results
    original_status: Optional[str] = None
    github_state: str = "open"
    
    # Comment enhancement results
    comments_enhanced: int = 0
    users_mentioned: int = 0
    
    def get_enhancement_summary(self) -> str:
        """Get a summary of enhancements applied"""
        enhancements = []
        
        if self.assignee_mapped:
            enhancements.append(f"assignee mapped ({self.original_assignee} → @{self.mapped_assignee})")
        
        if self.labels_created:
            enhancements.append(f"{len(self.labels_created)} labels auto-created")
        
        if self.labels_enhanced > 0:
            enhancements.append(f"{self.labels_enhanced} labels enhanced")
        
        if self.github_state == "closed":
            enhancements.append(f"migrated as closed (was {self.original_status})")
        
        if self.comments_enhanced > 0:
            enhancements.append(f"{self.comments_enhanced} comments enhanced")
        
        if self.users_mentioned > 0:
            enhancements.append(f"{self.users_mentioned} users @mentioned")
        
        return "; ".join(enhancements) if enhancements else "no enhancements applied"


@dataclass
class UserMappingStats:
    """Statistics about user mapping usage during migration"""
    
    total_users_encountered: int = 0
    users_mapped: int = 0
    users_unmapped: int = 0
    assignees_mapped: int = 0
    commenters_mapped: int = 0
    new_mentions_created: int = 0
    
    @property
    def mapping_rate(self) -> float:
        """Calculate the percentage of users that were successfully mapped"""
        if self.total_users_encountered == 0:
            return 0.0
        return (self.users_mapped / self.total_users_encountered) * 100
    
    def add_user_encounter(self, was_mapped: bool, user_type: str = "general"):
        """Record an encounter with a user during migration"""
        self.total_users_encountered += 1
        
        if was_mapped:
            self.users_mapped += 1
            
            if user_type == "assignee":
                self.assignees_mapped += 1
            elif user_type == "commenter":
                self.commenters_mapped += 1
                
        else:
            self.users_unmapped += 1
    
    def get_summary(self) -> str:
        """Get a summary string of mapping statistics"""
        if self.total_users_encountered == 0:
            return "No users encountered during migration"
        
        return (
            f"{self.users_mapped}/{self.total_users_encountered} users mapped "
            f"({self.mapping_rate:.1f}% success rate), "
            f"{self.assignees_mapped} assignees, {self.commenters_mapped} commenters, "
            f"{self.new_mentions_created} new @mentions created"
        )


@dataclass
class LabelEnhancementStats:
    """Statistics about label enhancement during migration"""
    
    original_labels: int = 0
    type_labels_added: int = 0
    priority_labels_added: int = 0
    status_labels_added: int = 0
    component_labels_added: int = 0
    labels_auto_created: List[str] = field(default_factory=list)
    
    @property
    def total_enhanced_labels(self) -> int:
        """Total number of labels after enhancement"""
        return (self.original_labels + self.type_labels_added + 
                self.priority_labels_added + self.status_labels_added + 
                self.component_labels_added)
    
    @property
    def enhancement_rate(self) -> float:
        """Calculate how many additional labels were added"""
        if self.original_labels == 0:
            return 0.0 if self.total_enhanced_labels == 0 else float('inf')
        return ((self.total_enhanced_labels - self.original_labels) / self.original_labels) * 100
    
    def get_summary(self) -> str:
        """Get a summary of label enhancements"""
        added = self.total_enhanced_labels - self.original_labels
        
        summary_parts = [f"{self.original_labels} original labels"]
        
        if added > 0:
            summary_parts.append(f"{added} enhanced labels added")
            
            details = []
            if self.type_labels_added > 0:
                details.append(f"{self.type_labels_added} type")
            if self.priority_labels_added > 0:
                details.append(f"{self.priority_labels_added} priority") 
            if self.status_labels_added > 0:
                details.append(f"{self.status_labels_added} status")
            if self.component_labels_added > 0:
                details.append(f"{self.component_labels_added} component")
                
            if details:
                summary_parts.append(f"({', '.join(details)})")
        
        if self.labels_auto_created:
            summary_parts.append(f"{len(self.labels_auto_created)} labels auto-created")
        
        return "; ".join(summary_parts)