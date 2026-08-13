"""Construction of the placeholder value set for one document.

This is the single place that decides what ``{{...}}`` names mean.  Adding a
placeholder is one entry here; nothing else in the module -- engine, routes,
storage, UI -- needs to know it exists, because the engine substitutes whatever
names it finds and reports the ones nobody supplied.

Precedence, widest to narrowest: built-in fields, then the settings' custom
placeholders, then the request's ad-hoc values.  So an operator can always
override a computed value for a single batch without changing the configuration.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Mapping

from document_generator.models.schemas import PaperMetadata
from document_generator.services.metadata_extractor import format_authors


def build_context(
    paper: PaperMetadata,
    *,
    acceptance_date: str = "",
    deadline: str = "",
    editor: str = "",
    journal: str = "",
    document_type: str = "",
    fee: str = "",
    currency: str = "",
    bank_details: str = "",
    invoice_number: str = "",
    invoice_date: str = "",
    custom: Mapping[str, str] | None = None,
    extra: Mapping[str, str] | None = None,
) -> Dict[str, str]:
    """Placeholder name -> value for one paper/document-type pair.

    Names are upper-cased; the engine's lookup is case-insensitive, so a template
    may write ``{{Title}}`` or ``{{title}}`` just as well.
    """
    authors = list(paper.authors or [])
    first_author = authors[0] if authors else ""
    # Surname heuristic for salutations: templates commonly want "Dear Dr Smith".
    surname = first_author.split()[-1] if first_author else ""

    curr = currency or "$"
    inv_num = invoice_number or (f"INV-{paper.reference_number}" if paper.reference_number else "")
    inv_date = invoice_date or acceptance_date or date.today().strftime("%d %B %Y")
    due_date = deadline or ""
    total_val = f"{curr} {fee}".strip() if fee else ""

    context: Dict[str, str] = {
        "TITLE": paper.title or "",
        "PAPER_TITLE": paper.title or "",
        "AUTHORS": format_authors(authors),
        "AUTHOR_LIST": "\n".join(authors),
        "AUTHOR_COUNT": str(len(authors)),
        "FIRST_AUTHOR": first_author,
        "CORRESPONDING_AUTHOR": first_author,
        "AUTHOR_SURNAME": surname,
        "CUSTOMER_NAME": first_author,
        "BILL_TO": first_author,
        "PAYEE": first_author,
        "REFERENCE_NUMBER": paper.reference_number or "",
        "REFERENCE_NO": paper.reference_number or "",
        "REF_NUMBER": paper.reference_number or "",
        "MANUSCRIPT_ID": paper.reference_number or "",
        "ACCEPT_DATE": acceptance_date,
        "ACCEPTANCE_DATE": acceptance_date,
        "DATE": acceptance_date or inv_date,
        "DEADLINE": due_date,
        "PAYMENT_DEADLINE": due_date,
        "DUE_DATE": due_date,
        "EDITOR": editor,
        "EDITOR_NAME": editor,
        "JOURNAL": journal,
        "JOURNAL_NAME": journal,
        "PAPER_NUMBER": str(paper.index),
        "PAPER_INDEX": str(paper.index),
        "SOURCE_FILENAME": paper.source_filename or "",
        "DOCUMENT_TYPE": document_type,
        # Invoice specific placeholders
        "FEE": fee,
        "PUBLICATION_FEE": fee,
        "AMOUNT": fee,
        "PRICE": fee,
        "CURRENCY": curr,
        "TOTAL_CHARGE_USD": fee,
        "TOTAL_CHARGE": total_val or fee,
        "TOTAL_AMOUNT": total_val or fee,
        "TOTAL_FEE": total_val or fee,
        "TOTAL": total_val or fee,
        "DISCOUNT": (extra or {}).get("DISCOUNT", "$0"),
        "INVOICE_NUMBER": inv_num,
        "INVOICE_NO": inv_num,
        "INV_NO": inv_num,
        "INV_NUM": inv_num,
        "INVOICE_DATE": inv_date,
        "INV_DATE": inv_date,
        "BANK_DETAILS": bank_details,
        "BANK_INFO": bank_details,
        "PAYMENT_INFO": bank_details,
        # Generation date, distinct from the operator-supplied acceptance date.
        "TODAY": date.today().strftime("%d %B %Y"),
        "YEAR": str(date.today().year),
    }

    for source in (custom or {}, extra or {}):
        for key, value in source.items():
            if not key:
                continue
            context[str(key).strip().upper()] = "" if value is None else str(value)

    return context
