import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for the Jira to GitHub migration tool"""
    
    # Jira settings
    jira_server_url: str
    jira_email: str
    jira_api_token: str
    
    # GitHub settings
    github_token: str
    github_repo_owner: str
    github_repo_name: str
    
    # Optional settings
    default_jira_project: Optional[str] = None
    dry_run: bool = False
    include_comments: bool = True
    include_attachments: bool = True
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        load_dotenv()
        
        required_vars = [
            'JIRA_SERVER_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN',
            'GITHUB_TOKEN', 'GITHUB_REPO_OWNER', 'GITHUB_REPO_NAME'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return cls(
            jira_server_url=os.getenv('JIRA_SERVER_URL'),
            jira_email=os.getenv('JIRA_EMAIL'),
            jira_api_token=os.getenv('JIRA_API_TOKEN'),
            default_jira_project=os.getenv('DEFAULT_JIRA_PROJECT'),
            github_token=os.getenv('GITHUB_TOKEN'),
            github_repo_owner=os.getenv('GITHUB_REPO_OWNER'),
            github_repo_name=os.getenv('GITHUB_REPO_NAME'),
            dry_run=os.getenv('DRY_RUN', 'false').lower() == 'true',
            include_comments=os.getenv('INCLUDE_COMMENTS', 'true').lower() == 'true',
            include_attachments=os.getenv('INCLUDE_ATTACHMENTS', 'true').lower() == 'true'
        )
