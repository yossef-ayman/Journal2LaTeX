"""
Academic Provider abstractions and implementations.
"""
from enrichment.providers.base import AcademicProvider
from enrichment.providers.openalex import OpenAlexProvider
from enrichment.providers.crossref import CrossrefProvider
from enrichment.providers.google_scholar import GoogleScholarProvider
from enrichment.providers.authors import AuthorProvider, OpenAlexAuthorProvider, GoogleScholarAuthorProvider

__all__ = [
    "AcademicProvider",
    "OpenAlexProvider",
    "CrossrefProvider",
    "GoogleScholarProvider",
    "AuthorProvider",
    "OpenAlexAuthorProvider",
    "GoogleScholarAuthorProvider"
]
