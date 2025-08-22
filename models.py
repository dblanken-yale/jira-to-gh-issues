from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class JiraIssue:
    """Data class representing a Jira issue"""
    key: str
    summary: str
    description: Optional[str]
    issue_type: str
    status: str
    priority: str
    assignee: Optional[str]
    reporter: str
    created: datetime
    updated: datetime
    labels: List[str]
    components: List[str]
    custom_fields: Dict[str, Any]
    issue_links: List[Dict[str, Any]]
    
    @classmethod
    def from_jira_data(cls, jira_data: Dict[str, Any]) -> 'JiraIssue':
        """Create JiraIssue from Jira API response data"""
        fields = jira_data['fields']
        
        return cls(
            key=jira_data['key'],
            summary=fields['summary'],
            description=fields.get('description', ''),
            issue_type=fields['issuetype']['name'],
            status=fields['status']['name'],
            priority=fields['priority']['name'] if fields.get('priority') else 'Medium',
            assignee=fields['assignee']['displayName'] if fields.get('assignee') else None,
            reporter=fields['reporter']['displayName'],
            created=datetime.fromisoformat(fields['created'].replace('Z', '+00:00')),
            updated=datetime.fromisoformat(fields['updated'].replace('Z', '+00:00')),
            labels=fields.get('labels', []),
            components=[comp['name'] for comp in fields.get('components', [])],
            custom_fields={k: v for k, v in fields.items() if k.startswith('customfield_')},
            issue_links=fields.get('issuelinks', [])
        )


@dataclass
class GitHubIssue:
    """Data class representing a GitHub issue to be created"""
    title: str
    body: str
    labels: List[str]
    assignees: List[str]
    milestone: Optional[str] = None
    
    def to_github_data(self) -> Dict[str, Any]:
        """Convert to GitHub API format"""
        data = {
            'title': self.title,
            'body': self.body,
            'labels': self.labels
        }
        if self.assignees:
            data['assignees'] = self.assignees
        if self.milestone:
            data['milestone'] = self.milestone
        return data


@dataclass
class MigrationResult:
    """Result of migrating a single Jira issue"""
    jira_key: str
    success: bool
    github_issue_number: Optional[int] = None
    github_url: Optional[str] = None
    error_message: Optional[str] = None
