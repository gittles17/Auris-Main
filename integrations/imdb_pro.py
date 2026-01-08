"""
IMDb Pro Integration - Fetches project and talent data from IMDb Pro.
Requires valid IMDb Pro subscription credentials.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "imdb_pro_cache.json"


@dataclass
class Project:
    """Represents a film/TV project from IMDb Pro."""
    imdb_id: str
    title: str
    project_type: str  # "movie", "tv_series", "tv_movie", etc.
    status: str  # "In Development", "Pre-Production", "Filming", "Post-Production", "Completed"
    release_date: Optional[str] = None
    studios: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    logline: Optional[str] = None
    budget: Optional[str] = None
    box_office: Optional[str] = None


@dataclass
class Person:
    """Represents a person from IMDb Pro."""
    imdb_id: str
    name: str
    primary_profession: Optional[str] = None
    known_for: Optional[List[str]] = None
    agent: Optional[str] = None
    manager: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None


@dataclass
class Company:
    """Represents a company from IMDb Pro."""
    imdb_id: str
    name: str
    company_type: Optional[str] = None
    projects: Optional[List[str]] = None
    contact_info: Optional[Dict[str, str]] = None


class IMDbProIntegration:
    """Integrates with IMDb Pro for industry data."""
    
    def __init__(self):
        self.username = os.getenv("IMDB_PRO_USERNAME")
        self.password = os.getenv("IMDB_PRO_PASSWORD")
        self._browser = None
        self._context = None
        self._page = None
        self._logged_in = False
        self._cache: Dict[str, Any] = {}
        self._cache_duration = timedelta(hours=4)
        self._load_cache()
    
    @property
    def is_configured(self) -> bool:
        """Check if IMDb Pro credentials are configured."""
        return bool(self.username and self.password)
    
    def _load_cache(self):
        """Load cached data from disk."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key in self._cache:
            item = self._cache[key]
            cached_at = datetime.fromisoformat(item.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at < self._cache_duration:
                return item.get("data")
        return None
    
    def _set_cached(self, key: str, data: Any):
        """Set item in cache."""
        self._cache[key] = {
            "cached_at": datetime.now().isoformat(),
            "data": data
        }
        self._save_cache()
    
    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                self._page = await self._context.new_page()
            except ImportError:
                raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")
    
    async def login(self) -> bool:
        """Log into IMDb Pro."""
        if not self.is_configured:
            print("IMDb Pro credentials not configured")
            return False
        
        if self._logged_in:
            return True
        
        await self._ensure_browser()
        
        try:
            # Navigate to IMDb Pro login
            await self._page.goto("https://pro.imdb.com/login", wait_until="networkidle")
            
            # Click "Sign in with IMDb" if present
            try:
                sign_in_btn = await self._page.wait_for_selector(
                    'a[href*="signin"], button:has-text("Sign in")', 
                    timeout=5000
                )
                if sign_in_btn:
                    await sign_in_btn.click()
                    await self._page.wait_for_load_state("networkidle")
            except Exception:
                pass
            
            # Fill in email
            email_field = await self._page.wait_for_selector(
                'input[type="email"], input[name="email"], #ap_email',
                timeout=10000
            )
            await email_field.fill(self.username)
            
            # Click continue/next if there's a two-step form
            try:
                continue_btn = await self._page.query_selector(
                    'input[type="submit"], button[type="submit"], .a-button-input'
                )
                if continue_btn:
                    await continue_btn.click()
                    await self._page.wait_for_load_state("networkidle")
            except Exception:
                pass
            
            # Fill in password
            password_field = await self._page.wait_for_selector(
                'input[type="password"], input[name="password"], #ap_password',
                timeout=10000
            )
            await password_field.fill(self.password)
            
            # Submit login
            submit_btn = await self._page.query_selector(
                '#signInSubmit, input[type="submit"], button[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
            
            # Wait for redirect to IMDb Pro
            await self._page.wait_for_url("**/pro.imdb.com/**", timeout=30000)
            
            self._logged_in = True
            print("Successfully logged into IMDb Pro")
            return True
            
        except Exception as e:
            print(f"IMDb Pro login failed: {e}")
            return False
    
    async def search_projects(self, query: str, status: Optional[str] = None) -> List[Project]:
        """Search for projects on IMDb Pro."""
        cache_key = f"projects:{query}:{status}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Project(**p) for p in cached]
        
        if not await self.login():
            return []
        
        try:
            # Navigate to search
            search_url = f"https://pro.imdb.com/search/title/?q={query}"
            if status:
                status_map = {
                    "development": "development",
                    "pre-production": "pre_prod",
                    "filming": "filming",
                    "post-production": "post_prod",
                    "completed": "completed"
                }
                if status.lower() in status_map:
                    search_url += f"&production_status={status_map[status.lower()]}"
            
            await self._page.goto(search_url, wait_until="networkidle")
            
            projects = []
            
            # Extract project cards
            cards = await self._page.query_selector_all('[data-testid="title-card"], .search-result, .title-result')
            
            for card in cards[:20]:
                try:
                    title_elem = await card.query_selector('a[href*="/title/"], .title-link, h3 a')
                    title = await title_elem.inner_text() if title_elem else "Unknown"
                    
                    href = await title_elem.get_attribute("href") if title_elem else ""
                    imdb_id = ""
                    if "/title/" in href:
                        imdb_id = href.split("/title/")[1].split("/")[0].split("?")[0]
                    
                    status_elem = await card.query_selector('.status, .production-status, [data-testid="status"]')
                    proj_status = await status_elem.inner_text() if status_elem else "Unknown"
                    
                    type_elem = await card.query_selector('.type, .title-type, [data-testid="type"]')
                    proj_type = await type_elem.inner_text() if type_elem else "movie"
                    
                    project = Project(
                        imdb_id=imdb_id,
                        title=title.strip(),
                        project_type=proj_type.strip().lower(),
                        status=proj_status.strip()
                    )
                    projects.append(project)
                    
                except Exception as e:
                    continue
            
            self._set_cached(cache_key, [asdict(p) for p in projects])
            return projects
            
        except Exception as e:
            print(f"Project search failed: {e}")
            return []
    
    async def search_people(self, query: str, profession: Optional[str] = None) -> List[Person]:
        """Search for people on IMDb Pro."""
        cache_key = f"people:{query}:{profession}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Person(**p) for p in cached]
        
        if not await self.login():
            return []
        
        try:
            search_url = f"https://pro.imdb.com/search/name/?q={query}"
            if profession:
                search_url += f"&profession={profession}"
            
            await self._page.goto(search_url, wait_until="networkidle")
            
            people = []
            
            cards = await self._page.query_selector_all('[data-testid="name-card"], .search-result, .name-result')
            
            for card in cards[:20]:
                try:
                    name_elem = await card.query_selector('a[href*="/name/"], .name-link, h3 a')
                    name = await name_elem.inner_text() if name_elem else "Unknown"
                    
                    href = await name_elem.get_attribute("href") if name_elem else ""
                    imdb_id = ""
                    if "/name/" in href:
                        imdb_id = href.split("/name/")[1].split("/")[0].split("?")[0]
                    
                    prof_elem = await card.query_selector('.profession, .primary-profession, [data-testid="profession"]')
                    primary_prof = await prof_elem.inner_text() if prof_elem else None
                    
                    person = Person(
                        imdb_id=imdb_id,
                        name=name.strip(),
                        primary_profession=primary_prof.strip() if primary_prof else None
                    )
                    people.append(person)
                    
                except Exception:
                    continue
            
            self._set_cached(cache_key, [asdict(p) for p in people])
            return people
            
        except Exception as e:
            print(f"People search failed: {e}")
            return []
    
    async def get_project_details(self, imdb_id: str) -> Optional[Project]:
        """Get detailed info for a specific project."""
        cache_key = f"project_detail:{imdb_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return Project(**cached)
        
        if not await self.login():
            return None
        
        try:
            await self._page.goto(f"https://pro.imdb.com/title/{imdb_id}/", wait_until="networkidle")
            
            title_elem = await self._page.query_selector('h1, .title-name, [data-testid="title"]')
            title = await title_elem.inner_text() if title_elem else "Unknown"
            
            status_elem = await self._page.query_selector('.production-status, [data-testid="status"]')
            status = await status_elem.inner_text() if status_elem else "Unknown"
            
            type_elem = await self._page.query_selector('.title-type, [data-testid="type"]')
            proj_type = await type_elem.inner_text() if type_elem else "movie"
            
            logline_elem = await self._page.query_selector('.logline, .plot, [data-testid="plot"]')
            logline = await logline_elem.inner_text() if logline_elem else None
            
            release_elem = await self._page.query_selector('.release-date, [data-testid="release-date"]')
            release_date = await release_elem.inner_text() if release_elem else None
            
            # Get studios/companies
            studios = []
            studio_elems = await self._page.query_selector_all('.company-link, [data-testid="company"] a')
            for elem in studio_elems[:5]:
                studio_name = await elem.inner_text()
                if studio_name:
                    studios.append(studio_name.strip())
            
            # Get genres
            genres = []
            genre_elems = await self._page.query_selector_all('.genre, [data-testid="genre"]')
            for elem in genre_elems:
                genre = await elem.inner_text()
                if genre:
                    genres.append(genre.strip())
            
            project = Project(
                imdb_id=imdb_id,
                title=title.strip(),
                project_type=proj_type.strip().lower(),
                status=status.strip(),
                release_date=release_date,
                studios=studios if studios else None,
                genres=genres if genres else None,
                logline=logline
            )
            
            self._set_cached(cache_key, asdict(project))
            return project
            
        except Exception as e:
            print(f"Failed to get project details: {e}")
            return None
    
    async def get_person_details(self, imdb_id: str) -> Optional[Person]:
        """Get detailed info for a specific person including contacts."""
        cache_key = f"person_detail:{imdb_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return Person(**cached)
        
        if not await self.login():
            return None
        
        try:
            await self._page.goto(f"https://pro.imdb.com/name/{imdb_id}/", wait_until="networkidle")
            
            name_elem = await self._page.query_selector('h1, .name-title, [data-testid="name"]')
            name = await name_elem.inner_text() if name_elem else "Unknown"
            
            prof_elem = await self._page.query_selector('.primary-profession, [data-testid="profession"]')
            profession = await prof_elem.inner_text() if prof_elem else None
            
            # Get known for titles
            known_for = []
            kf_elems = await self._page.query_selector_all('.known-for a, [data-testid="known-for"] a')
            for elem in kf_elems[:5]:
                title = await elem.inner_text()
                if title:
                    known_for.append(title.strip())
            
            # Get representation
            contact_info = {}
            
            agent_elem = await self._page.query_selector('.agent, [data-testid="agent"]')
            agent = await agent_elem.inner_text() if agent_elem else None
            
            manager_elem = await self._page.query_selector('.manager, [data-testid="manager"]')
            manager = await manager_elem.inner_text() if manager_elem else None
            
            # Try to get contact details
            contact_elems = await self._page.query_selector_all('.contact-item, [data-testid="contact"]')
            for elem in contact_elems:
                text = await elem.inner_text()
                if "email" in text.lower():
                    contact_info["email"] = text.split(":")[-1].strip()
                elif "phone" in text.lower():
                    contact_info["phone"] = text.split(":")[-1].strip()
            
            person = Person(
                imdb_id=imdb_id,
                name=name.strip(),
                primary_profession=profession.strip() if profession else None,
                known_for=known_for if known_for else None,
                agent=agent,
                manager=manager,
                contact_info=contact_info if contact_info else None
            )
            
            self._set_cached(cache_key, asdict(person))
            return person
            
        except Exception as e:
            print(f"Failed to get person details: {e}")
            return None
    
    async def get_upcoming_releases(self, months_ahead: int = 6) -> List[Project]:
        """Get upcoming theatrical/streaming releases."""
        cache_key = f"upcoming:{months_ahead}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Project(**p) for p in cached]
        
        if not await self.login():
            return []
        
        try:
            # Navigate to release calendar or use search with date filters
            await self._page.goto(
                "https://pro.imdb.com/search/title/?production_status=completed&release_date=upcoming",
                wait_until="networkidle"
            )
            
            projects = []
            cards = await self._page.query_selector_all('[data-testid="title-card"], .search-result, .title-result')
            
            for card in cards[:30]:
                try:
                    title_elem = await card.query_selector('a[href*="/title/"], .title-link')
                    title = await title_elem.inner_text() if title_elem else "Unknown"
                    
                    href = await title_elem.get_attribute("href") if title_elem else ""
                    imdb_id = ""
                    if "/title/" in href:
                        imdb_id = href.split("/title/")[1].split("/")[0]
                    
                    release_elem = await card.query_selector('.release-date, [data-testid="release"]')
                    release_date = await release_elem.inner_text() if release_elem else None
                    
                    project = Project(
                        imdb_id=imdb_id,
                        title=title.strip(),
                        project_type="movie",
                        status="Completed",
                        release_date=release_date
                    )
                    projects.append(project)
                    
                except Exception:
                    continue
            
            self._set_cached(cache_key, [asdict(p) for p in projects])
            return projects
            
        except Exception as e:
            print(f"Failed to get upcoming releases: {e}")
            return []
    
    async def get_projects_in_development(self, studio: Optional[str] = None) -> List[Project]:
        """Get projects currently in development."""
        cache_key = f"in_dev:{studio or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Project(**p) for p in cached]
        
        if not await self.login():
            return []
        
        try:
            url = "https://pro.imdb.com/search/title/?production_status=development,pre_prod"
            if studio:
                url += f"&companies={studio}"
            
            await self._page.goto(url, wait_until="networkidle")
            
            projects = []
            cards = await self._page.query_selector_all('[data-testid="title-card"], .search-result')
            
            for card in cards[:30]:
                try:
                    title_elem = await card.query_selector('a[href*="/title/"]')
                    title = await title_elem.inner_text() if title_elem else "Unknown"
                    
                    href = await title_elem.get_attribute("href") if title_elem else ""
                    imdb_id = ""
                    if "/title/" in href:
                        imdb_id = href.split("/title/")[1].split("/")[0]
                    
                    status_elem = await card.query_selector('.status, .production-status')
                    status = await status_elem.inner_text() if status_elem else "In Development"
                    
                    project = Project(
                        imdb_id=imdb_id,
                        title=title.strip(),
                        project_type="movie",
                        status=status.strip()
                    )
                    projects.append(project)
                    
                except Exception:
                    continue
            
            self._set_cached(cache_key, [asdict(p) for p in projects])
            return projects
            
        except Exception as e:
            print(f"Failed to get projects in development: {e}")
            return []
    
    async def close(self):
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._logged_in = False
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
    
    def format_project_list(self, projects: List[Project]) -> str:
        """Format projects for display."""
        if not projects:
            return "No projects found."
        
        lines = []
        for p in projects:
            studios = ", ".join(p.studios) if p.studios else "N/A"
            release = p.release_date or "TBD"
            lines.append(f"- **{p.title}** ({p.project_type}) | Status: {p.status} | Release: {release} | Studios: {studios}")
        
        return "\n".join(lines)
    
    def format_person_list(self, people: List[Person]) -> str:
        """Format people for display."""
        if not people:
            return "No people found."
        
        lines = []
        for p in people:
            prof = p.primary_profession or "N/A"
            rep = []
            if p.agent:
                rep.append(f"Agent: {p.agent}")
            if p.manager:
                rep.append(f"Manager: {p.manager}")
            rep_str = " | ".join(rep) if rep else "No rep info"
            lines.append(f"- **{p.name}** ({prof}) | {rep_str}")
        
        return "\n".join(lines)


# Synchronous wrapper for use in Streamlit
class IMDbProSync:
    """Synchronous wrapper for IMDb Pro integration."""
    
    def __init__(self):
        self._async_client = IMDbProIntegration()
    
    @property
    def is_configured(self) -> bool:
        return self._async_client.is_configured
    
    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def login(self) -> bool:
        return self._run_async(self._async_client.login())
    
    def search_projects(self, query: str, status: Optional[str] = None) -> List[Project]:
        return self._run_async(self._async_client.search_projects(query, status))
    
    def search_people(self, query: str, profession: Optional[str] = None) -> List[Person]:
        return self._run_async(self._async_client.search_people(query, profession))
    
    def get_project_details(self, imdb_id: str) -> Optional[Project]:
        return self._run_async(self._async_client.get_project_details(imdb_id))
    
    def get_person_details(self, imdb_id: str) -> Optional[Person]:
        return self._run_async(self._async_client.get_person_details(imdb_id))
    
    def get_upcoming_releases(self, months_ahead: int = 6) -> List[Project]:
        return self._run_async(self._async_client.get_upcoming_releases(months_ahead))
    
    def get_projects_in_development(self, studio: Optional[str] = None) -> List[Project]:
        return self._run_async(self._async_client.get_projects_in_development(studio))
    
    def format_project_list(self, projects: List[Project]) -> str:
        return self._async_client.format_project_list(projects)
    
    def format_person_list(self, people: List[Person]) -> str:
        return self._async_client.format_person_list(people)
    
    def close(self):
        self._run_async(self._async_client.close())

