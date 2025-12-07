"""Main TUI application for Termijob."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
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
    ]
    
    def __init__(self, job, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
    
    def compose(self) -> ComposeResult:
        with Container(id="job-detail-modal"):
            yield Static(f"[bold]{self.job.title}[/bold]", id="job-title")
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
            with ScrollableContainer(id="description-container"):
                yield Static(self.job.description, id="job-description")
            yield Static("─" * 60, classes="separator")
            yield Static("[bold]Original Posting:[/bold]", id="raw-label")
            with ScrollableContainer(id="raw-text-container"):
                yield Static(self.job.raw_text, id="raw-text-display")
            with Horizontal(id="modal-buttons"):
                yield Button("Close", id="close-btn", variant="primary")
                yield Button("Delete", id="delete-btn", variant="error")
        yield Footer()
    
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
    """Main dashboard screen."""
    
    BINDINGS = [
        Binding("a", "add_job", "Add Job"),
        Binding("l", "list_all", "List All"),
        Binding("s", "search", "Search"),
        Binding("q", "quit", "Quit"),
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
        with Container(id="main-container"):
            yield Static("[bold]Termijob - Upwork Job Manager[/bold]", id="app-title")
            yield Static("", id="stats-display")
            
            with Horizontal(id="main-buttons"):
                yield Button("Add Job [A]", id="add-btn", variant="success")
                yield Button("List All [L]", id="list-all-btn", variant="primary")
                yield Button("Search [S]", id="search-btn", variant="default")
            
            yield Static("[bold]Categories:[/bold]", id="categories-label")
            with ScrollableContainer(id="categories-container"):
                yield Vertical(id="categories-list")
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_stats()
    
    def on_screen_resume(self) -> None:
        self.refresh_stats()
    
    def refresh_stats(self) -> None:
        total = self.repo.get_job_count()
        stats = self.query_one("#stats-display", Static)
        stats.update(f"Total jobs stored: [cyan]{total}[/cyan]")
        
        self._refresh_categories()
    
    def _refresh_categories(self) -> None:
        """Refresh the categories list with buttons."""
        categories = self.repo.get_categories_with_counts()
        categories_list = self.query_one("#categories-list", Vertical)
        
        # Remove all existing children synchronously
        children = list(categories_list.children)
        for child in children:
            child.remove()
        
        self.category_map.clear()
        
        if categories:
            for cat, count in categories:
                safe_id = self._sanitize_id(cat)
                self.category_map[safe_id] = cat
                # Don't use id - just use name attribute to store category info
                btn = Button(
                    f"• {cat} ({count})", 
                    name=safe_id,
                    classes="category-btn"
                )
                categories_list.mount(btn)
        else:
            categories_list.mount(Static("  No jobs yet. Add your first job!"))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            self.action_add_job()
        elif event.button.id == "list-all-btn":
            self.action_list_all()
        elif event.button.id == "search-btn":
            self.action_search()
        elif event.button.name and "category-btn" in event.button.classes:
            # Category button pressed
            safe_id = event.button.name
            category = self.category_map.get(safe_id, safe_id.replace("_", " ").title())
            self.app.push_screen(JobListScreen(category=category))
    
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
    
    #main-container {
        padding: 1 2;
        height: 100%;
    }
    
    #app-title {
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }
    
    #stats-display {
        text-align: center;
        padding: 1;
        margin-bottom: 1;
    }
    
    #main-buttons {
        align: center middle;
        height: auto;
        margin: 1 0;
    }
    
    #main-buttons Button {
        margin: 0 1;
    }
    
    #categories-label {
        margin-top: 1;
        padding: 0 1;
    }
    
    #categories-container {
        height: auto;
        max-height: 50%;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
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
    }
    
    .category-btn:hover {
        background: $primary-darken-1;
    }
    
    .category-btn:focus {
        text-style: bold;
    }
    
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
    }
    
    #search-results {
        height: 70%;
    }
    
    #job-detail-modal {
        width: 90%;
        height: 90%;
        background: $surface;
        border: solid $primary;
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
    
    #description-container {
        height: 25%;
        border: solid $accent;
        padding: 1;
        margin: 0 0 1 0;
    }
    
    #raw-text-container {
        height: 25%;
        border: solid $secondary;
        padding: 1;
        margin: 0 0 1 0;
        background: $surface-darken-1;
    }
    
    #modal-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    
    #modal-buttons Button {
        margin: 0 1;
    }
    
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
    
    .category-btn {
        width: 100%;
        margin: 1 0;
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
