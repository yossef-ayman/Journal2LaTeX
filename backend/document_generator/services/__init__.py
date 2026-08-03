"""Service layer of the Document Generator module.

Sub-modules are imported lazily by their consumers rather than re-exported here,
so importing one service never drags in the converter's analyzer (which
``metadata_extractor`` touches) or the PDF backend.
"""
