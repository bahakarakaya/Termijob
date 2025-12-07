"""Main TUI application for Termijob."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Static, Label, 
    TextArea, ListView, ListItem, Input, Select, DataTable
)
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.message import Message
from textual import work
from rich.text import Text

from .repository import JobRepository
from .llm import LLMParser, CATEGORIES, ParsedJob


class JobDetailModal(ModalScreen):
    """Modal to display job details."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("d", "delete_job", "Delete", show=True),
        Binding("g", "scroll_top", "Top", show=True),
        Binding("G", "scroll_bottom", "Bottom", show=True),
    ]
    
    # Custom footer hint for arrow keys
    FOOTER_HINT = "↑↓ Scroll"
    
    def __init__(self, job, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
    
    def compose(self) -> ComposeResult:
        with Container(id="job-detail-modal"):
            yield Static(f"[bold]{self.job.title}[/bold]", id="job-title")
            with VerticalScroll(id="modal-scroll-container"):
                with Horizontal(id="job-meta-row"):
                    yield Static(f"[cyan]📁 {self.job.category}[/cyan]", classes="meta-item")
                    yield Static(f"[green]💰 {self.job.budget or 'N/A'}[/green]", classes="meta-item")
                    yield Static(f"[yellow]📋 {self.job.job_type or 'N/A'}[/yellow]", classes="meta-item")
                with Horizontal(id="job-meta-row2"):
                    yield Static(f"[magenta]⭐ {self.job.experience_level or 'N/A'}[/magenta]", classes="meta-item")
                    yield Static(f"[blue]📍 {self.job.client_location or 'N/A'}[/blue]", classes="meta-item")
                yield Static("─" * 60, classes="separator")
                yield Static("[bold]Skills Required:[/bold]")
                yield Static(f"  {self.job.skills or 'None specified'}", id="skills-display")
                yield Static("─" * 60, classes="separator")
                yield Static("[bold]Description:[/bold]")
                yield Static(self.job.description, id="job-description")
                yield Static("─" * 60, classes="separator")
                yield Static("[bold]Original Posting:[/bold]", id="raw-label")
                yield Static(self.job.raw_text, id="raw-text-display")
            with Horizontal(id="modal-buttons"):
                yield Button("Close", id="close-btn", variant="primary")
                yield Button("Delete", id="delete-btn", variant="error")
            yield Static("[dim]↑↓ Scroll[/dim]", id="scroll-hint")
        yield Footer()
    
    def on_mount(self) -> None:
        # Focus the scroll container for keyboard navigation
        self.query_one("#modal-scroll-container", VerticalScroll).focus()
    
    def action_scroll_top(self) -> None:
        self.query_one("#modal-scroll-container", VerticalScroll).scroll_home()
    
    def action_scroll_bottom(self) -> None:
        self.query_one("#modal-scroll-container", VerticalScroll).scroll_end()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss(False)
        elif event.button.id == "delete-btn":
            self.dismiss(True)  # Signal to delete
    
    def action_dismiss(self) -> None:
        self.dismiss(False)
    
    def action_delete_job(self) -> None:
        self.dismiss(True)


class AddJobScreen(Screen):
    """Screen for adding a new job posting."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+s", "submit_job", "Submit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="add-job-container"):
            yield Static("[bold]Add New Job Posting[/bold]", id="add-job-title")
            yield Static("Paste the job posting text below:", classes="instruction")
            yield TextArea(id="job-text-area")
            with Horizontal(id="add-job-buttons"):
                yield Button("Parse & Save", id="parse-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")
            yield Static("", id="status-message")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "parse-btn":
            self.action_submit_job()
        elif event.button.id == "cancel-btn":
            self.action_go_back()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    @work(exclusive=True)
    async def action_submit_job(self) -> None:
        text_area = self.query_one("#job-text-area", TextArea)
        status = self.query_one("#status-message", Static)
        raw_text = text_area.text.strip()
        
        if not raw_text:
            status.update("[red]Please paste a job posting first![/red]")
            return
        
        status.update("[yellow]Parsing job posting with LLM...[/yellow]")
        
        try:
            # Parse job using LLM
            parser = LLMParser()
            parsed = parser.parse_job(raw_text)
            
            # Save to database
            repo = JobRepository()
            job_data = {
                "title": parsed.title,
                "category": parsed.category,
                "description": parsed.description,
                "skills": ", ".join(parsed.skills) if parsed.skills else None,
                "budget": parsed.budget,
                "client_location": parsed.client_location,
                "experience_level": parsed.experience_level,
                "job_type": parsed.job_type,
                "raw_text": raw_text,
            }
            repo.add_job(job_data)
            
            status.update(f"[green]Job saved! Category: {parsed.category}[/green]")
            
            # Clear text area and go back after a short delay
            text_area.clear()
            self.app.pop_screen()
            self.app.notify(f"Job '{parsed.title[:30]}...' added to {parsed.category}")
            
        except Exception as e:
            status.update(f"[red]Error: {str(e)}[/red]")


class JobListScreen(Screen):
    """Screen for listing jobs."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete_selected", "Delete"),
    ]
    
    def __init__(self, category: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.repo = JobRepository()
    
    def compose(self) -> ComposeResult:
        yield Header()
        title = f"Jobs: {self.category}" if self.category else "All Jobs"
        with Container(id="job-list-container"):
            yield Static(f"[bold]{title}[/bold]", id="list-title")
            yield DataTable(id="jobs-table", cursor_type="row")
        yield Footer()
    
    def on_mount(self) -> None:
        self.load_jobs()
    
    def load_jobs(self) -> None:
        table = self.query_one("#jobs-table", DataTable)
        table.clear(columns=True)
        
        table.add_columns("ID", "Title", "Category", "Budget", "Type", "Date")
        
        if self.category:
            jobs = self.repo.get_jobs_by_category(self.category)
        else:
            jobs = self.repo.get_all_jobs()
        
        for job in jobs:
            table.add_row(
                str(job.id),
                job.title[:40] + "..." if len(job.title) > 40 else job.title,
                job.category,
                job.budget or "-",
                job.job_type or "-",
                job.created_at.strftime("%Y-%m-%d") if job.created_at else "-",
                key=str(job.id),
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_selected_job()
    
    def _open_selected_job(self) -> None:
        """Open the currently selected job in detail modal."""
        table = self.query_one("#jobs-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                job_id = int(row_key[0])
                job = self.repo.get_job(job_id)
                if job:
                    self.app.push_screen(JobDetailModal(job), self.handle_modal_result)
    
    def handle_modal_result(self, should_delete: bool) -> None:
        if should_delete:
            table = self.query_one("#jobs-table", DataTable)
            if table.cursor_row is not None:
                row_key = table.get_row_at(table.cursor_row)
                if row_key:
                    job_id = int(row_key[0])
                    self.repo.delete_job(job_id)
                    self.load_jobs()
                    self.app.notify("Job deleted")
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        self.load_jobs()
        self.app.notify("Refreshed")
    
    def action_delete_selected(self) -> None:
        table = self.query_one("#jobs-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                job_id = int(row_key[0])
                self.repo.delete_job(job_id)
                self.load_jobs()
                self.app.notify("Job deleted")


class SearchScreen(Screen):
    """Screen for searching jobs."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo = JobRepository()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="search-container"):
            yield Static("[bold]Search Jobs[/bold]", id="search-title")
            with Horizontal(id="search-bar"):
                yield Input(placeholder="Enter search terms...", id="search-input")
                yield Button("Search", id="search-btn", variant="primary")
            yield DataTable(id="search-results", cursor_type="row")
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one("#search-results", DataTable)
        table.add_columns("ID", "Title", "Category", "Budget", "Skills")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            self.perform_search()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.perform_search()
    
    def perform_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.strip()
        
        if not query:
            return
        
        table = self.query_one("#search-results", DataTable)
        table.clear()
        
        jobs = self.repo.search_jobs(query)
        
        for job in jobs:
            table.add_row(
                str(job.id),
                job.title[:35] + "..." if len(job.title) > 35 else job.title,
                job.category,
                job.budget or "-",
                (job.skills[:30] + "...") if job.skills and len(job.skills) > 30 else (job.skills or "-"),
                key=str(job.id),
            )
        
        self.app.notify(f"Found {len(jobs)} job(s)")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_selected_job()
    
    def _open_selected_job(self) -> None:
        """Open the currently selected job in detail modal."""
        table = self.query_one("#search-results", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                job_id = int(row_key[0])
                job = self.repo.get_job(job_id)
                if job:
                    self.app.push_screen(JobDetailModal(job), self.handle_modal_result)
    
    def handle_modal_result(self, should_delete: bool) -> None:
        if should_delete:
            table = self.query_one("#search-results", DataTable)
            if table.cursor_row is not None:
                row_key = table.get_row_at(table.cursor_row)
                if row_key:
                    job_id = int(row_key[0])
                    self.repo.delete_job(job_id)
                    self.perform_search()
                    self.app.notify("Job deleted")
    
    def action_go_back(self) -> None:
        self.app.pop_screen()


class MainScreen(Screen):
    """Main dashboard screen with sidebar navigation."""
    
    BINDINGS = [
        Binding("a", "add_job", "Add Job", show=True),
        Binding("l", "list_all", "List All", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("j", "nav_down", "Down", show=False),
        Binding("k", "nav_up", "Up", show=False),
        Binding("down", "nav_down", "Down", show=False),
        Binding("up", "nav_up", "Up", show=False),
        Binding("enter", "select_menu", "Select", show=False),
    ]
    
    MENU_ITEMS = [
        ("dashboard", "📊 Dashboard", None),
        ("add_job", "➕ Add Job", "add_job"),
        ("list_all", "📋 List All", "list_all"),
        ("search", "🔍 Search", "search"),
        ("quit", "🚪 Quit", "quit"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo = JobRepository()
        self.category_map = {}
        self.selected_menu_index = 0
    
    def _sanitize_id(self, name: str) -> str:
        """Convert category name to valid widget ID."""
        return name.replace(" ", "_").replace("/", "_").lower()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="dashboard-layout"):
            # Left Sidebar
            with Vertical(id="sidebar"):
                yield Static("[bold]Termijob[/bold]", id="sidebar-title")
                yield Static("─" * 18, classes="sidebar-divider")
                with Vertical(id="nav-menu"):
                    for idx, (key, label, _) in enumerate(self.MENU_ITEMS):
                        classes = "nav-item selected" if idx == 0 else "nav-item"
                        yield Static(label, id=f"nav-{key}", classes=classes)
            
            # Right Main Content
            with Vertical(id="main-content"):
                # Stats Section
                yield Static("", id="stats-display")
                
                # Categories Section
                with Vertical(id="categories-section"):
                    yield Static("─ Categories ", id="categories-header")
                    with ScrollableContainer(id="categories-container"):
                        yield Vertical(id="categories-list")
                
                # Recent Jobs Section
                with Vertical(id="recent-section"):
                    yield Static("─ Recent Jobs ", id="recent-header")
                    yield DataTable(id="recent-jobs-table", cursor_type="row")
        yield Footer()
    
    def on_mount(self) -> None:
        # Setup recent jobs table columns first
        table = self.query_one("#recent-jobs-table", DataTable)
        table.add_columns("ID", "Title", "Category", "Date")
        # Then refresh data
        self.refresh_dashboard()
    
    def on_screen_resume(self) -> None:
        self.refresh_dashboard()
    
    def refresh_dashboard(self) -> None:
        """Refresh all dashboard data."""
        # Update stats
        total = self.repo.get_job_count()
        stats = self.query_one("#stats-display", Static)
        stats.update(f"[bold]📈 Stats:[/bold] [cyan]{total}[/cyan] Jobs Stored")
        
        # Update categories
        self._refresh_categories()
        
        # Update recent jobs
        self._refresh_recent_jobs()
    
    def _refresh_categories(self) -> None:
        """Refresh the categories list."""
        categories = self.repo.get_categories_with_counts()
        categories_list = self.query_one("#categories-list", Vertical)
        
        # Remove existing children
        for child in list(categories_list.children):
            child.remove()
        
        self.category_map.clear()
        
        if categories:
            for cat, count in categories:
                safe_id = self._sanitize_id(cat)
                self.category_map[safe_id] = cat
                btn = Button(
                    f"• {cat} ({count})", 
                    name=safe_id,
                    classes="category-btn"
                )
                categories_list.mount(btn)
        else:
            categories_list.mount(Static("[dim]No categories yet[/dim]", classes="empty-message"))
    
    def _refresh_recent_jobs(self) -> None:
        """Refresh the recent jobs table."""
        table = self.query_one("#recent-jobs-table", DataTable)
        table.clear()
        
        recent_jobs = self.repo.get_recent_jobs(5)
        
        if recent_jobs:
            for job in recent_jobs:
                table.add_row(
                    str(job.id),
                    job.title[:30] + "..." if len(job.title) > 30 else job.title,
                    job.category[:15] if job.category else "-",
                    job.created_at.strftime("%m/%d") if job.created_at else "-",
                    key=str(job.id),
                )
        else:
            # Add placeholder row
            table.add_row("-", "No recent activity", "-", "-")
    
    def _update_menu_selection(self) -> None:
        """Update visual selection in navigation menu."""
        for idx, (key, _, _) in enumerate(self.MENU_ITEMS):
            nav_item = self.query_one(f"#nav-{key}", Static)
            if idx == self.selected_menu_index:
                nav_item.add_class("selected")
            else:
                nav_item.remove_class("selected")
    
    def action_nav_down(self) -> None:
        """Navigate down in menu."""
        self.selected_menu_index = (self.selected_menu_index + 1) % len(self.MENU_ITEMS)
        self._update_menu_selection()
    
    def action_nav_up(self) -> None:
        """Navigate up in menu."""
        self.selected_menu_index = (self.selected_menu_index - 1) % len(self.MENU_ITEMS)
        self._update_menu_selection()
    
    def action_select_menu(self) -> None:
        """Execute selected menu action."""
        _, _, action = self.MENU_ITEMS[self.selected_menu_index]
        if action == "add_job":
            self.action_add_job()
        elif action == "list_all":
            self.action_list_all()
        elif action == "search":
            self.action_search()
        elif action == "quit":
            self.app.exit()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name and "category-btn" in event.button.classes:
            safe_id = event.button.name
            category = self.category_map.get(safe_id, safe_id.replace("_", " ").title())
            self.app.push_screen(JobListScreen(category=category))
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in recent jobs table."""
        table = self.query_one("#recent-jobs-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key and row_key[0] != "-":
                job_id = int(row_key[0])
                job = self.repo.get_job(job_id)
                if job:
                    self.app.push_screen(JobDetailModal(job), self._handle_modal_result)
    
    def _handle_modal_result(self, should_delete: bool) -> None:
        if should_delete:
            table = self.query_one("#recent-jobs-table", DataTable)
            if table.cursor_row is not None:
                row_key = table.get_row_at(table.cursor_row)
                if row_key and row_key[0] != "-":
                    job_id = int(row_key[0])
                    self.repo.delete_job(job_id)
                    self.refresh_dashboard()
                    self.app.notify("Job deleted")
    
    def action_add_job(self) -> None:
        self.app.push_screen(AddJobScreen())
    
    def action_list_all(self) -> None:
        self.app.push_screen(JobListScreen())
    
    def action_search(self) -> None:
        self.app.push_screen(SearchScreen())


class CategorySelectScreen(Screen):
    """Screen for selecting a category to filter jobs."""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo = JobRepository()
        self.category_map = {}  # Maps sanitized ID to actual category name
    
    def _sanitize_id(self, name: str) -> str:
        """Convert category name to valid widget ID."""
        return name.replace(" ", "_").replace("/", "_").lower()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="category-select-container"):
            yield Static("[bold]Select a Category[/bold]", id="category-title")
            with ScrollableContainer(id="category-buttons"):
                categories = self.repo.get_categories_with_counts()
                for cat, count in categories:
                    safe_id = self._sanitize_id(cat)
                    self.category_map[safe_id] = cat
                    yield Button(f"{cat} ({count})", id=f"cat-{safe_id}", classes="category-btn")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith("cat-"):
            safe_id = event.button.id[4:]  # Remove "cat-" prefix
            category = self.category_map.get(safe_id, safe_id)
            self.app.push_screen(JobListScreen(category=category))
    
    def action_go_back(self) -> None:
        self.app.pop_screen()


class TermiJobApp(App):
    """Main TUI Application for managing Upwork job postings."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    /* Dashboard Layout */
    #dashboard-layout {
        height: 100%;
        width: 100%;
    }
    
    /* Sidebar */
    #sidebar {
        width: 22;
        height: 100%;
        background: $surface-darken-1;
        border-right: solid $primary;
        padding: 0;
    }
    
    #sidebar-title {
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    .sidebar-divider {
        color: $primary;
        text-align: center;
    }
    
    #nav-menu {
        padding: 1 0;
        height: auto;
    }
    
    .nav-item {
        padding: 0 1;
        height: auto;
        color: $text;
    }
    
    .nav-item.selected {
        background: $primary;
        color: $text;
        text-style: bold reverse;
    }
    
    .nav-item:hover {
        background: $primary-darken-1;
    }
    
    /* Main Content Area */
    #main-content {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }
    
    #stats-display {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: round $accent;
        margin-bottom: 1;
    }
    
    /* Categories Section */
    #categories-section {
        height: 40%;
        border: round $primary;
        padding: 0 1 1 1;
        margin-bottom: 1;
    }
    
    #categories-header {
        color: $primary;
        text-style: bold;
        height: auto;
        padding: 0;
        margin-bottom: 1;
    }
    
    #categories-container {
        height: 1fr;
        padding: 0;
    }
    
    #categories-list {
        height: auto;
    }
    
    .category-btn {
        width: 100%;
        text-align: left;
        margin: 0;
        padding: 0 1;
        background: transparent;
        border: none;
        min-width: 0;
        height: auto;
        color: $text;
    }
    
    .category-btn:hover {
        background: $primary-darken-2;
    }
    
    .category-btn:focus {
        text-style: bold;
        background: $primary-darken-1;
    }
    
    .empty-message {
        padding: 1;
        color: $text-muted;
    }
    
    /* Recent Jobs Section */
    #recent-section {
        height: 1fr;
        border: round $secondary;
        padding: 0 1 1 1;
    }
    
    #recent-header {
        color: $secondary;
        text-style: bold;
        height: auto;
        padding: 0;
        margin-bottom: 1;
    }
    
    #recent-jobs-table {
        height: 1fr;
    }
    
    /* Add Job Screen */
    #add-job-container {
        padding: 1 2;
        height: 100%;
    }
    
    #add-job-title {
        text-align: center;
        padding: 1;
        background: $success;
        margin-bottom: 1;
    }
    
    .instruction {
        padding: 0 1;
        margin-bottom: 1;
    }
    
    #job-text-area {
        height: 60%;
        border: solid $primary;
    }
    
    #add-job-buttons {
        align: center middle;
        height: auto;
        margin: 1 0;
    }
    
    #add-job-buttons Button {
        margin: 0 1;
    }
    
    #status-message {
        text-align: center;
        padding: 1;
    }
    
    /* Job List Screen */
    #job-list-container {
        padding: 1 2;
        height: 100%;
    }
    
    #list-title {
        text-align: center;
        padding: 1;
        background: $primary;
        margin-bottom: 1;
    }
    
    #jobs-table {
        height: 80%;
    }
    
    /* Search Screen */
    #search-container {
        padding: 1 2;
        height: 100%;
    }
    
    #search-title {
        text-align: center;
        padding: 1;
        background: $primary;
        margin-bottom: 1;
    }
    
    #search-bar {
        height: auto;
        margin-bottom: 1;
    }
    
    #search-input {
        width: 80%;
    }
    
    #search-btn {
        margin-left: 1;
        background: $primary;
        color: $text;
    }
    
    #search-results {
        height: 70%;
    }
    
    /* Job Detail Modal */
    #job-detail-modal {
        width: 90%;
        height: 90%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    
    #job-title {
        padding: 1;
        background: $primary;
        margin-bottom: 1;
        text-align: center;
    }
    
    #job-meta-row, #job-meta-row2 {
        height: auto;
        margin: 0 0 1 0;
    }
    
    .meta-item {
        margin-right: 3;
    }
    
    .separator {
        color: $primary;
        margin: 1 0;
    }
    
    #skills-display {
        color: $text-muted;
        margin-bottom: 1;
    }
    
    #modal-scroll-container {
        height: 1fr;
        border: round $accent;
        padding: 1;
        margin: 0 0 1 0;
    }
    
    #job-description, #raw-text-display {
        margin: 0 0 1 0;
    }
    
    #modal-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    
    #modal-buttons Button {
        margin: 0 1;
    }
    
    #scroll-hint {
        text-align: center;
        margin-top: 1;
    }
    
    /* Category Select Screen */
    #category-select-container {
        padding: 1 2;
        height: 100%;
    }
    
    #category-title {
        text-align: center;
        padding: 1;
        background: $primary;
        margin-bottom: 1;
    }
    
    #category-buttons {
        height: auto;
        max-height: 70%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "show_categories", "Categories"),
    ]
    
    TITLE = "Termijob"
    SUB_TITLE = "Upwork Job Manager"
    
    def on_mount(self) -> None:
        self.push_screen(MainScreen())
    
    def action_show_categories(self) -> None:
        self.push_screen(CategorySelectScreen())


def main():
    """Entry point for the application."""
    app = TermiJobApp()
    app.run()


if __name__ == "__main__":
    main()
