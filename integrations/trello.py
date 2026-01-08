"""
Trello Integration - Fetches project status from Trello boards.
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"


class TrelloIntegration:
    """Integrates with Trello to fetch project status."""
    
    def __init__(self):
        self.api_key = os.getenv("TRELLO_API_KEY")
        self.token = os.getenv("TRELLO_TOKEN")
        self.board_id = os.getenv("TRELLO_BOARD_ID")
        self.base_url = "https://api.trello.com/1"
        self.projects: List[Dict] = []
    
    @property
    def is_configured(self) -> bool:
        """Check if Trello is configured."""
        return bool(self.api_key and self.token and self.board_id)
    
    def get_projects(self) -> List[Dict]:
        """Fetch projects from Trello or local export."""
        if self.is_configured:
            try:
                return self._fetch_from_api()
            except Exception as e:
                print(f"Warning: Trello API error: {e}")
        
        return self._load_from_export()
    
    def _fetch_from_api(self) -> List[Dict]:
        """Fetch projects from Trello API."""
        lists_url = f"{self.base_url}/boards/{self.board_id}/lists"
        params = {
            "key": self.api_key,
            "token": self.token,
            "cards": "all"
        }
        
        response = requests.get(lists_url, params=params)
        response.raise_for_status()
        lists_data = response.json()
        
        projects = []
        for lst in lists_data:
            list_name = lst.get("name", "Unknown")
            for card in lst.get("cards", []):
                project = {
                    "name": card.get("name", ""),
                    "status": list_name,
                    "description": card.get("desc", ""),
                    "due_date": card.get("due"),
                    "labels": [l.get("name", "") for l in card.get("labels", [])],
                    "url": card.get("shortUrl", ""),
                    "last_activity": card.get("dateLastActivity")
                }
                
                for label in project["labels"]:
                    if label:
                        project["creative_director"] = label
                        break
                
                projects.append(project)
        
        self.projects = projects
        return projects
    
    def _load_from_export(self) -> List[Dict]:
        """Load projects from a local Trello JSON export."""
        export_path = DATA_DIR / "trello_export.json"
        
        if not export_path.exists():
            return []
        
        try:
            with open(export_path, "r") as f:
                data = json.load(f)
            
            lists_by_id = {lst["id"]: lst["name"] for lst in data.get("lists", [])}
            
            projects = []
            for card in data.get("cards", []):
                if card.get("closed"):
                    continue
                
                list_id = card.get("idList", "")
                project = {
                    "name": card.get("name", ""),
                    "status": lists_by_id.get(list_id, "Unknown"),
                    "description": card.get("desc", ""),
                    "due_date": card.get("due"),
                    "labels": [l.get("name", "") for l in card.get("labels", [])],
                    "url": card.get("shortUrl", ""),
                    "last_activity": card.get("dateLastActivity")
                }
                
                for label in project["labels"]:
                    if label:
                        project["creative_director"] = label
                        break
                
                projects.append(project)
            
            self.projects = projects
            return projects
            
        except Exception as e:
            print(f"Warning: Could not load Trello export: {e}")
            return []
    
    def format_project_summary(self) -> str:
        """Format projects for AI context."""
        if not self.projects:
            return "No project data available. Configure Trello API or upload trello_export.json"
        
        by_status: Dict[str, List] = {}
        for project in self.projects:
            status = project.get("status", "Unknown")
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(project)
        
        lines = []
        for status, projects in by_status.items():
            lines.append(f"\n{status} ({len(projects)} projects):")
            for p in projects[:5]:
                name = p.get("name", "Unknown")
                cd = p.get("creative_director", "Unassigned")
                due = p.get("due_date", "No due date")
                if due:
                    try:
                        due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                        due = due_dt.strftime("%b %d")
                    except:
                        pass
                lines.append(f"  - {name} | CD: {cd} | Due: {due}")
            
            if len(projects) > 5:
                lines.append(f"  ... and {len(projects) - 5} more")
        
        return "\n".join(lines)

