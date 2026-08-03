"""Reference-number generation.

Pattern: ``<JournalCode><MMDDYY><BatchOrder><Suffix>``

* ``JournalCode`` the journal's short code -- ``JSAP``, ``IJM``, ``JNS`` -- taken
  from the module settings and overridable per batch, because one installation
  routinely serves several journals;
* ``MM`` month, ``DD`` day, ``YY`` last two digits of the year -- the acceptance
  date of the batch, so every document produced in one run carries the same date
  component and the numbers of a batch sort together;
* ``BatchOrder`` the 1-based order of the paper within the current batch,
  zero-padded;
* ``Suffix`` a suffix configured in the module's settings.

Example, for journal code ``JSAP``: ``JSAP07302601A``, ``JSAP07302602A``.

The journal code is a *component of the number*, not a label: the ``Ref. ``
wording that introduces it belongs to the template and is never generated here,
so whatever the template says in front of the number stays exactly as written.

An optional literal prefix may still be placed in front of the whole number for
operators who file by year or series.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

# Formats an operator plausibly types into the acceptance-date field.  Parsed
# only to derive MM/DD/YY; the date shown in the document itself is always the
# operator's own text, never a reformatted version of it.
_DATE_FORMATS = (
    "%d %B %Y",
    "%d %b %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
)

# Two digits covers a 99-paper batch; beyond that the field simply widens rather
# than wrapping around and issuing a duplicate reference.
_INDEX_WIDTH = 2


def parse_reference_date(text: str) -> Optional[date]:
    """Best-effort parse of a free-text date.  ``None`` if unrecognised."""
    candidate = (text or "").strip()
    if not candidate:
        return None
    candidate = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s{2,}", " ", candidate)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def date_component(reference_date: Optional[date] = None) -> str:
    """The ``MMDDYY`` part of a reference number."""
    day = reference_date or date.today()
    return f"{day.month:02d}{day.day:02d}{day.year % 100:02d}"


def normalise_journal_code(code: Optional[str]) -> str:
    """A journal code as it belongs in a reference number.

    Upper-cased and stripped of spaces and punctuation, so ``jsap``, ``J-SAP``
    and ``JSAP`` all produce the same, stable identifier -- an operator should
    not be able to split one journal's numbering in two by typing it differently.
    """
    return re.sub(r"[^A-Za-z0-9]", "", (code or "")).upper()


def build_reference_number(
    index: int,
    reference_date: Optional[date] = None,
    suffix: str = "A",
    prefix: Optional[str] = None,
    journal_code: Optional[str] = None,
) -> str:
    """Assemble one reference number.

    ``index`` is the 1-based position of the paper in the batch.  An empty
    ``journal_code`` simply omits that component, which keeps reference numbers
    issued before the code was configured reproducible.
    """
    order = max(1, int(index))
    number = (
        f"{normalise_journal_code(journal_code)}"
        f"{date_component(reference_date)}"
        f"{order:0{_INDEX_WIDTH}d}"
        f"{(suffix or '').strip()}"
    )
    return f"{(prefix or '').strip()}{number}"
