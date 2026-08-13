"""The vocabulary of dynamic fields a template can carry.

A mapping turns an ordinary Word document into a template by recording, for each
field, the literal text in the document that represents it.  The field keys are
deliberately the same keys :mod:`document_generator.services.context_builder`
produces, so a mapped field and a ``{{PLACEHOLDER}}`` of the same name resolve to
exactly the same value -- one value vocabulary, two ways of pointing at it.

Adding a field is one entry here (and, if it is a new value, one line in the
context builder).  Nothing else -- wizard, engine, storage, routes -- needs to
change, because they all iterate this registry.
"""

from __future__ import annotations

from typing import Dict, List

from document_generator.models.schemas import TemplateFieldInfo

# Ordered: the wizard presents the fields in this sequence.
_FIELDS: Dict[str, TemplateFieldInfo] = {
    "TITLE": TemplateFieldInfo(
        key="TITLE",
        label="Paper title",
        description="The title of the accepted manuscript, read from each paper.",
        required=True,
    ),
    "AUTHORS": TemplateFieldInfo(
        key="AUTHORS",
        label="Authors",
        description="The author list, read from each paper.",
        required=True,
    ),
    "REFERENCE_NUMBER": TemplateFieldInfo(
        key="REFERENCE_NUMBER",
        label="Reference number",
        description="Generated per paper from the acceptance date and batch order.",
        required=True,
    ),
    "ACCEPTANCE_DATE": TemplateFieldInfo(
        key="ACCEPTANCE_DATE",
        label="Acceptance date",
        description="Entered once for the whole batch and used verbatim.",
    ),
    "DEADLINE": TemplateFieldInfo(
        key="DEADLINE",
        label="Deadline",
        description="Payment or revision deadline, entered once for the batch.",
    ),
    "JOURNAL": TemplateFieldInfo(
        key="JOURNAL",
        label="Journal name",
        description="From the generator settings, unless overridden for a batch.",
    ),
    "EDITOR": TemplateFieldInfo(
        key="EDITOR",
        label="Editor name",
        description="From the generator settings, unless overridden for a batch.",
    ),
    "FIRST_AUTHOR": TemplateFieldInfo(
        key="FIRST_AUTHOR",
        label="Corresponding author",
        description="The first author of the paper, for salutations and billing.",
    ),
    "FEE": TemplateFieldInfo(
        key="FEE",
        label="Publication Fee",
        description="Publication charge/fee amount for the paper.",
    ),
    "CURRENCY": TemplateFieldInfo(
        key="CURRENCY",
        label="Currency",
        description="Currency symbol or code (e.g., $, USD, EUR).",
    ),
    "TOTAL_AMOUNT": TemplateFieldInfo(
        key="TOTAL_AMOUNT",
        label="Total Amount",
        description="Total calculated amount including currency or fees.",
    ),
    "INVOICE_NUMBER": TemplateFieldInfo(
        key="INVOICE_NUMBER",
        label="Invoice Number",
        description="Unique invoice reference number.",
    ),
    "INVOICE_DATE": TemplateFieldInfo(
        key="INVOICE_DATE",
        label="Invoice Date",
        description="Date of invoice issuance.",
    ),
    "DUE_DATE": TemplateFieldInfo(
        key="DUE_DATE",
        label="Payment Due Date",
        description="Deadline for publication fee payment.",
    ),
    "BANK_DETAILS": TemplateFieldInfo(
        key="BANK_DETAILS",
        label="Bank Details",
        description="Bank account, IBAN, SWIFT, and payment instructions.",
    ),
    "CUSTOMER_NAME": TemplateFieldInfo(
        key="CUSTOMER_NAME",
        label="Bill To / Customer Name",
        description="Name of the person or entity being billed.",
    ),
    "AUTHOR_ADDRESS": TemplateFieldInfo(
        key="AUTHOR_ADDRESS",
        label="Author Address / Affiliation",
        description="Address or institution of the author/payee.",
    ),
}


def list_fields() -> List[TemplateFieldInfo]:
    """Every mappable field, in presentation order."""
    return list(_FIELDS.values())


def is_known(key: str) -> bool:
    return (key or "").strip().upper() in _FIELDS


def get_field(key: str) -> TemplateFieldInfo:
    """Look up one field. Raises ``KeyError`` for an unknown key."""
    return _FIELDS[(key or "").strip().upper()]


def register_field(info: TemplateFieldInfo) -> None:
    """Add a mappable field at runtime.

    The extension point for future document kinds: a certificate template that
    needs a "conference name" field registers it here and the wizard offers it,
    with no other change to the module.
    """
    _FIELDS[info.key.strip().upper()] = info
