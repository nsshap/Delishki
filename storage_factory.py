"""Factory for creating storage instances."""
from notion_storage import NotionStorage


def get_storage():
    """Get storage instance (Notion)."""
    return NotionStorage()


