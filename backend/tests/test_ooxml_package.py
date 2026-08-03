"""The package as a whole, on the real papers only.

Nothing synthetic here on purpose: the point of these assertions is that a real
manuscript survives being opened, resolved and written back.
"""

from __future__ import annotations

import zipfile

from document_engine.ooxml.package import Package


def test_opening_a_paper_parses_every_text_part(paper) -> None:
    package = Package.open(paper)
    assert "word/document.xml" in package.parts
    assert package.document is not None
    assert list(package.paragraphs())


def test_nothing_is_changed_by_merely_reading(paper) -> None:
    """The read path must have no write path in it."""
    package = Package.open(paper)
    assert package.changed_parts() == []
    serialized = package.serialize()
    for name, part in package.parts.items():
        assert serialized[name] is package.entries[name]


def test_saving_an_unedited_package_preserves_every_part(paper, tmp_path) -> None:
    package = Package.open(paper)
    out = tmp_path / "out.docx"
    package.save(out)
    with zipfile.ZipFile(out) as written, zipfile.ZipFile(paper) as original:
        assert written.namelist() == original.namelist()
        for name in original.namelist():
            assert written.read(name) == original.read(name), name


def test_styles_are_shared_across_parts(paper) -> None:
    package = Package.open(paper)
    assert package.styles.styles, "a Word document always ships styles.xml"
    for part in package.parts.values():
        for block in part.blocks:
            if hasattr(block, "effective"):
                assert block.effective is not None


def test_relationships_resolve_image_targets(paper) -> None:
    rels = Package.open(paper).relationships()
    assert rels
    assert all(rid.startswith("rId") for rid in rels)


def test_every_drawing_names_a_relationship_that_exists(paper) -> None:
    """A figure whose ``r:embed`` points nowhere is a figure that will not
    survive being rewritten -- worth catching at parse time, not export time."""
    package = Package.open(paper)
    rels = package.relationships()
    for paragraph in package.paragraphs():
        for drawing in paragraph.drawings:
            if drawing.relationship_id:
                assert drawing.relationship_id in rels
