"""What the engine can currently do.

The engine is built in phases, and the frontend needs to know which of them are
live so it can show a capability rather than guess at one.  Reporting this from
the backend -- instead of hard-coding a phase number in the UI -- means a
half-deployed environment tells the truth about itself.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

# Bumped by the phase that implements each capability.  Phase 1 added the
# physical layer: a .docx parses into anchored blocks with formatting resolved
# through the style cascade.  Phase 2 adds the semantic layer on top of it -- the
# engine can now say what a paragraph *is*, with the confidence and evidence
# behind each judgement.  Phase 3 adds writing: accepted suggestions are spliced
# into the byte ranges they affect, previewed before anything is saved, and the
# rest of the package is copied through as the same bytes it arrived as.  Phase 4
# adds the assistant: plugins that read the semantic model and propose edits,
# which only the Phase 3 writer can apply, and only once a person accepts them.
# ``assistant`` stays false until a model-backed provider is registered: the
# plugins are deterministic, and saying otherwise would overstate what is here.
_CAPABILITIES = {
    "parse": True,       # Phase 1: package -> anchored blocks + resolved styles
    "extract": True,     # Phase 2: blocks -> an understood document model
    "edit": True,        # Phase 3: write accepted edits back into the original
    "diff": True,        # Phase 3: original / suggested / accept / reject
    "suggest": True,     # Phase 4: deterministic suggestion plugins
    "preview": True,     # Phase 3: preview a decision set before saving
    "assistant": False,  # Phase 6: a real DocumentAssistant provider
}


class EngineStatus(BaseModel):
    """Which parts of the engine are live in this deployment."""

    available: bool = True
    phase: int = Field(..., description="Highest fully implemented phase.")
    capabilities: dict[str, bool] = Field(
        ..., description="Capability name -> implemented."
    )


@router.get("/status", response_model=EngineStatus)
def get_status() -> EngineStatus:
    return EngineStatus(phase=4, capabilities=dict(_CAPABILITIES))
