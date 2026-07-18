from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class BlockType(str, Enum):
    """Supported document block types."""

    PARAGRAPH = "paragraph"
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"
    LIST = "list"
    AUTHOR_IMAGE = "author_image"
    LOGO = "logo"


class DocumentBlock(BaseModel):
    """Generic block representing an element in a document section with position tracking."""

    type: BlockType
    content: dict
    block_index: int = 0
    original_page_number: Optional[int] = None
    original_order: int = 0
    source_location: Optional[str] = None


class SectionModel(BaseModel):
    """Document section preserving the order of nested blocks."""

    title: str
    level: int
    blocks: List[DocumentBlock]


class AuthorModel(BaseModel):
    """Extended Pydantic model representing an author."""

    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    photo_path: Optional[str] = None


class AuthorBiography(BaseModel):
    """Structured author biography metadata."""

    author_name: str
    image_path: Optional[str] = None
    biography_text: str


class DocumentModel(BaseModel):
    """Extended Pydantic model representing a structured document with biographies."""

    title: str = ""
    authors: List[AuthorModel] = []
    abstract: str = ""
    keywords: List[str] = []
    sections: List[SectionModel] = []
    references: List[str] = []
    author_biographies: List[AuthorBiography] = []
    received_date: Optional[str] = ""
    revised_date: Optional[str] = ""
    accepted_date: Optional[str] = ""
    published_date: Optional[str] = ""
    volume: Optional[str] = ""
    issue: Optional[str] = ""
    year: Optional[str] = ""
    doi: Optional[str] = ""
