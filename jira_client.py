from typing import List, Optional, Dict, Any
from atlassian import Jira
from models import JiraIssue
from config import Config


class JiraClient:
    """Client for interacting with Jira API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.jira = Jira(
            url=config.jira_server_url,
            username=config.jira_email,
            password=config.jira_api_token,
            cloud=True
        )
    
    def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        """Get a single Jira issue by key"""
        try:
            issue_data = self.jira.issue(issue_key)
            return JiraIssue.from_jira_data(issue_data)
        except Exception as e:
            print(f"Error fetching Jira issue {issue_key}: {e}")
            return None
    
    def get_issues_by_keys(self, issue_keys: List[str]) -> List[JiraIssue]:
        """Get multiple Jira issues by their keys"""
        issues = []
        for key in issue_keys:
            issue = self.get_issue(key)
            if issue:
                issues.append(issue)
        return issues
    
    def search_issues(self, jql: str, max_results: int = 50, start_at: int = 0) -> List[JiraIssue]:
        """Search for issues using JQL with pagination support"""
        try:
            # Try using the existing jql method but with different parameter names
            # Some versions use 'startAt' instead of 'start'
            if start_at > 0:
                # Try the REST API directly using the existing session
                search_results = self.jira.get(
                    'rest/api/2/search',
                    params={
                        'jql': jql,
                        'maxResults': max_results,
                        'startAt': start_at,
                        'fields': '*all'
                    }
                )
            else:
                # For start_at=0, use the standard method
                search_results = self.jira.jql(jql, limit=max_results)

            issues = []
            for issue_data in search_results['issues']:
                issues.append(JiraIssue.from_jira_data(issue_data))
            return issues
        except Exception as e:
            print(f"Error searching Jira issues with pagination: {e}")
            # Fall back to original method without pagination
            try:
                search_results = self.jira.jql(jql, limit=max_results)
                issues = []
                for issue_data in search_results['issues']:
                    issues.append(JiraIssue.from_jira_data(issue_data))
                return issues
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                return []
    
    def get_issue_count(self, jql: str) -> int:
        """Get the total count of issues matching a JQL query without fetching all data"""
        try:
            # Try with a large batch to get as accurate count as possible
            search_results = self.jira.jql(jql, limit=5000)  # Maximum allowed

            # Check if 'total' field exists (older API format)
            if 'total' in search_results:
                return search_results['total']

            # For newer API without total field, count issues in response
            issue_count = len(search_results.get('issues', []))

            # If it's the last page, we have the exact count
            if search_results.get('isLast', True):
                return issue_count

            # If there are more pages, we need to continue paginating
            # Count all issues by making multiple requests
            total_count = issue_count
            next_token = search_results.get('nextPageToken')

            while next_token and not search_results.get('isLast', True):
                try:
                    search_results = self.jira.jql(jql, limit=5000, start=total_count)
                    batch_count = len(search_results.get('issues', []))
                    total_count += batch_count
                    next_token = search_results.get('nextPageToken')

                    if batch_count == 0:  # Safety break
                        break
                except:
                    break

            return total_count

        except Exception as e:
            print(f"Error counting Jira issues: {e}")
            return 0
    
    def get_project_issues(self, project_key: str, status: Optional[str] = None) -> List[JiraIssue]:
        """Get all issues from a specific project"""
        jql = f"project = {project_key}"
        if status:
            jql += f" AND status = '{status}'"
        return self.search_issues(jql)
    
    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get comments for a specific issue"""
        try:
            comments = self.jira.issue_get_comments(issue_key)
            return comments.get('comments', [])
        except Exception as e:
            print(f"Error fetching comments for {issue_key}: {e}")
            return []
    
    def get_issue_attachments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get attachments for a specific issue"""
        try:
            issue_data = self.jira.issue(issue_key, fields='attachment')
            return issue_data['fields'].get('attachment', [])
        except Exception as e:
            print(f"Error fetching attachments for {issue_key}: {e}")
            return []
