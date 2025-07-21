import os
import requests
import tempfile
import mimetypes
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from config import Config
from github import Repository
import base64


class AttachmentService:
    """Service for downloading Jira attachments and uploading to GitHub"""
    
    def __init__(self, config: Config, github_repo: Repository):
        self.config = config
        self.github_repo = github_repo
        self.temp_dir = tempfile.mkdtemp(prefix="jira_attachments_")
        
    def download_and_upload_attachments(self, jira_attachments: List[Dict], issue_key: str) -> List[Dict]:
        """Download Jira attachments and upload to GitHub, return GitHub file info"""
        uploaded_files = []
        
        for attachment in jira_attachments:
            try:
                # Download from Jira
                local_file = self._download_jira_attachment(attachment)
                if not local_file:
                    continue
                
                # Upload to GitHub
                github_file = self._upload_to_github(local_file, attachment, issue_key)
                if github_file:
                    uploaded_files.append(github_file)
                
                # Clean up local file
                try:
                    os.unlink(local_file)
                except:
                    pass
                    
            except Exception as e:
                print(f"Error processing attachment {attachment.get('filename', 'unknown')}: {e}")
                continue
        
        return uploaded_files
    
    def _download_jira_attachment(self, attachment: Dict) -> Optional[str]:
        """Download a single attachment from Jira"""
        try:
            filename = attachment.get('filename', 'unknown_file')
            download_url = attachment.get('content', '')
            
            if not download_url:
                print(f"No download URL for {filename}")
                return None
            
            # Prepare authentication for Jira
            auth = (self.config.jira_email, self.config.jira_api_token)
            
            # Download the file
            response = requests.get(download_url, auth=auth, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            local_path = os.path.join(self.temp_dir, filename)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded {filename} ({attachment.get('size', 0)} bytes)")
            return local_path
            
        except Exception as e:
            print(f"Failed to download {attachment.get('filename', 'unknown')}: {e}")
            return None
    
    def _upload_to_github(self, local_file: str, attachment_info: Dict, issue_key: str) -> Optional[Dict]:
        """Upload a file to GitHub repository"""
        try:
            filename = attachment_info.get('filename', 'unknown_file')
            
            # Create a path in the repository for attachments
            # Using format: attachments/ISSUE-KEY/filename
            github_path = f"attachments/{issue_key}/{filename}"
            
            # Read file content
            with open(local_file, 'rb') as f:
                content = f.read()
            
            # Encode for GitHub API
            content_b64 = base64.b64encode(content).decode('utf-8')
            
            # Check if file already exists
            try:
                existing_file = self.github_repo.get_contents(github_path)
                # Update existing file
                result = self.github_repo.update_file(
                    path=github_path,
                    message=f"Update attachment {filename} for {issue_key}",
                    content=content_b64,
                    sha=existing_file.sha
                )
            except Exception as e:
                print(f"Exception when checking for existing file: {type(e).__name__}: {e}")
                # Create new file
                result = self.github_repo.create_file(
                    path=github_path,
                    message=f"Add attachment {filename} for {issue_key}",
                    content=content_b64
                )
            
            # Get the raw download URL
            download_url = result['content'].download_url
            
            # Return file info
            file_info = {
                'filename': filename,
                'github_path': github_path,
                'download_url': download_url,
                'raw_url': download_url,
                'size': attachment_info.get('size', len(content)),
                'mime_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            }
            
            print(f"Uploaded {filename} to GitHub: {github_path}")
            return file_info
            
        except Exception as e:
            print(f"Failed to upload {attachment_info.get('filename', 'unknown')} to GitHub: {e}")
            return None
    
    def cleanup(self):
        """Clean up temporary directory"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
