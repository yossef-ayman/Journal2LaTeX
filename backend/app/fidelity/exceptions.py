"""Custom Exception Hierarchy for the Visual Fidelity Engine."""


class FidelityError(Exception):
    """Base exception for all visual fidelity engine errors."""
    pass


class ConfigurationError(FidelityError):
    """Raised when FidelityConfig or RenderingConfig validation fails."""
    pass


class RenderingError(FidelityError):
    """Raised when document page rasterization or rendering fails."""
    pass


class DocxConversionError(RenderingError):
    """Raised when converting a DOCX file to a reference PDF fails."""
    pass


class MatchingError(FidelityError):
    """Raised when page alignment or matching strategy fails."""
    pass


class MetricError(FidelityError):
    """Raised when a similarity metric plugin computation fails fatally."""
    pass


class ReportGenerationError(FidelityError):
    """Raised when aggregating or compiling the FidelityReport fails."""
    pass
