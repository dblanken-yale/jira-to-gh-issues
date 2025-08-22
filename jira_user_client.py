from typing import List, Dict, Any, Set
from atlassian import Jira
from config import Config
from datetime import datetime
import json


class JiraUserClient:
    """Extended Jira client for user discovery and project member extraction"""
    
    def __init__(self, config: Config):
        self.config = config
        self.jira = Jira(
            url=config.jira_server_url,
            username=config.jira_email,
            password=config.jira_api_token,
            cloud=True
        )
    
    def get_project_roles(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all roles defined for a project"""
        try:
            roles = self.jira.get_project_roles(project_key)
            return list(roles.items()) if isinstance(roles, dict) else roles
        except Exception as e:
            print(f"Error fetching project roles for {project_key}: {e}")
            return []
    
    def get_project_role_members(self, project_key: str, role_id: str) -> List[Dict[str, Any]]:
        """Get all users assigned to a specific project role"""
        try:
            role_actors = self.jira.get_project_role_actors(project_key, role_id)
            users = []
            
            if 'actors' in role_actors:
                for actor in role_actors['actors']:
                    if actor.get('type') == 'atlassian-user-role-actor':
                        users.append({
                            'account_id': actor.get('actorUser', {}).get('accountId'),
                            'display_name': actor.get('actorUser', {}).get('displayName'),
                            'email_address': actor.get('actorUser', {}).get('emailAddress'),
                            'role': role_actors.get('name', 'Unknown'),
                            'source': 'role_member'
                        })
            
            return users
        except Exception as e:
            print(f"Error fetching role members for {project_key}, role {role_id}: {e}")
            return []
    
    def get_assignable_users(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all users who can be assigned to issues in the project"""
        try:
            # Use the assignable user search endpoint
            users_data = self.jira.get_assignable_users_for_projects(project_key)
            users = []
            
            if isinstance(users_data, list):
                for user in users_data:
                    users.append({
                        'account_id': user.get('accountId'),
                        'display_name': user.get('displayName'),
                        'email_address': user.get('emailAddress'),
                        'active': user.get('active', True),
                        'source': 'assignable'
                    })
            
            return users
        except Exception as e:
            print(f"Error fetching assignable users for {project_key}: {e}")
            return []
    
    def extract_users_from_project_issues(self, project_key: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        """Extract all unique users from project issues (reporters, assignees, commenters)"""
        try:
            # Get all issues from the project
            jql = f"project = {project_key} ORDER BY created DESC"
            search_results = self.jira.jql(jql, limit=max_results)
            
            unique_users = {}
            user_activity = {}
            
            # Process issues for reporters and assignees
            for issue in search_results.get('issues', []):
                fields = issue['fields']
                issue_key = issue['key']
                
                # Track reporter
                reporter = fields.get('reporter')
                if reporter:
                    user_id = reporter.get('accountId')
                    if user_id:
                        unique_users[user_id] = {
                            'account_id': user_id,
                            'display_name': reporter.get('displayName'),
                            'email_address': reporter.get('emailAddress'),
                            'source': 'issue_reporter'
                        }
                        user_activity[user_id] = user_activity.get(user_id, 0) + 1
                
                # Track assignee
                assignee = fields.get('assignee')
                if assignee:
                    user_id = assignee.get('accountId')
                    if user_id:
                        unique_users[user_id] = {
                            'account_id': user_id,
                            'display_name': assignee.get('displayName'),
                            'email_address': assignee.get('emailAddress'),
                            'source': 'issue_assignee'
                        }
                        user_activity[user_id] = user_activity.get(user_id, 0) + 1
                
                # Get comments for this issue and track commenters
                try:
                    comments = self.jira.issue_get_comments(issue_key)
                    for comment in comments.get('comments', []):
                        author = comment.get('author', {})
                        user_id = author.get('accountId')
                        if user_id:
                            unique_users[user_id] = {
                                'account_id': user_id,
                                'display_name': author.get('displayName'),
                                'email_address': author.get('emailAddress'),
                                'source': 'issue_commenter'
                            }
                            user_activity[user_id] = user_activity.get(user_id, 0) + 1
                except Exception:
                    # Skip comment processing if it fails, continue with other issues
                    pass
            
            # Add activity count to user data
            users_list = []
            for user_id, user_data in unique_users.items():
                user_data['issue_activity_count'] = user_activity.get(user_id, 0)
                users_list.append(user_data)
            
            return users_list
            
        except Exception as e:
            print(f"Error extracting users from project issues {project_key}: {e}")
            return []
    
    def get_comprehensive_project_users(self, project_key: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all users associated with a project from multiple sources.
        Returns a dictionary keyed by user account ID with comprehensive user info.
        """
        print(f"🔍 Discovering users for project {project_key}...")
        
        all_users = {}
        
        # 1. Get users from project roles
        print("📋 Fetching project role members...")
        try:
            roles = self.get_project_roles(project_key)
            for role_name, role_url in roles:
                # Extract role ID from URL
                role_id = role_url.split('/')[-1] if role_url else None
                if role_id:
                    role_members = self.get_project_role_members(project_key, role_id)
                    for user in role_members:
                        user_id = user.get('account_id')
                        if user_id:
                            if user_id not in all_users:
                                all_users[user_id] = user.copy()
                                all_users[user_id]['roles'] = []
                                all_users[user_id]['sources'] = set()
                            
                            all_users[user_id]['roles'].append(user['role'])
                            all_users[user_id]['sources'].add('role_member')
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch project roles: {e}")
        
        # 2. Get assignable users
        print("👥 Fetching assignable users...")
        try:
            assignable_users = self.get_assignable_users(project_key)
            for user in assignable_users:
                user_id = user.get('account_id')
                if user_id:
                    if user_id not in all_users:
                        all_users[user_id] = user.copy()
                        all_users[user_id]['roles'] = []
                        all_users[user_id]['sources'] = set()
                    
                    # Merge data
                    all_users[user_id]['active'] = user.get('active', True)
                    all_users[user_id]['sources'].add('assignable')
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch assignable users: {e}")
        
        # 3. Get users from issue history
        print("📝 Extracting users from issue history (this may take a moment)...")
        try:
            issue_users = self.extract_users_from_project_issues(project_key)
            for user in issue_users:
                user_id = user.get('account_id')
                if user_id:
                    if user_id not in all_users:
                        all_users[user_id] = user.copy()
                        all_users[user_id]['roles'] = []
                        all_users[user_id]['sources'] = set()
                    
                    # Merge data
                    all_users[user_id]['issue_activity_count'] = user.get('issue_activity_count', 0)
                    all_users[user_id]['sources'].add('issue_history')
        except Exception as e:
            print(f"⚠️  Warning: Could not extract users from issues: {e}")
        
        # Convert sets to lists for JSON serialization
        for user_id, user_data in all_users.items():
            user_data['sources'] = list(user_data['sources'])
            user_data['roles'] = list(set(user_data.get('roles', [])))  # Remove duplicates
            
            # Ensure all users have required fields
            user_data.setdefault('display_name', 'Unknown User')
            user_data.setdefault('email_address', None)
            user_data.setdefault('active', True)
            user_data.setdefault('issue_activity_count', 0)
        
        print(f"✅ Found {len(all_users)} unique users across all sources")
        return all_users