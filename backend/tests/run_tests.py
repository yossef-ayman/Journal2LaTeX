"""A standalone runner for environments where pytest is not installed.

``pytest`` is the intended way to run this suite and the tests are written for
it.  This runner exists because the suite must be verifiable in a container that
has no package index, and a test suite nobody can run is not a test suite.  It
supports the small slice of pytest the suite actually uses -- module-level test
functions, ``tmp_path``, and the parametrised fixtures in ``conftest`` -- and
nothing more.

    python3 tests/run_tests.py
"""

from __future__ import annotations

import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BACKEND = TESTS.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))


class _Skip(Exception):
    pass


class _FakePytest:
    @staticmethod
    def skip(reason: str = "") -> None:
        raise _Skip(reason)

    @staticmethod
    def fixture(*args, **kwargs):
        def wrap(fn):
            return fn
        return wrap if not args else args[0]

    class raises:
        def __init__(self, exc):
            self.exc = exc

        def __enter__(self):
            return self

        def __exit__(self, kind, value, tb):
            if kind is None:
                raise AssertionError(f"{self.exc.__name__} was not raised")
            return issubclass(kind, self.exc)


sys.modules.setdefault("pytest", _FakePytest)  # type: ignore[arg-type]

PAPERS = ["normal_paper", "the_role", "with_author_photo", "with_charts"]


def _arguments(func, paper_name: str, tmp: Path):
    kwargs = {}
    for name in func.__code__.co_varnames[: func.__code__.co_argcount]:
        if name == "paper":
            kwargs[name] = TESTS / f"{paper_name}.docx"
        elif name == "document_bytes":
            with zipfile.ZipFile(TESTS / f"{paper_name}.docx") as archive:
                kwargs[name] = archive.read("word/document.xml")
        elif name == "tmp_path":
            kwargs[name] = tmp
    return kwargs


def main() -> int:
    import importlib

    modules = sorted(p.stem for p in TESTS.glob("test_*.py"))
    passed = failed = skipped = 0
    failures = []

    for module_name in modules:
        module = importlib.import_module(module_name)
        for name in sorted(vars(module)):
            func = getattr(module, name)
            if not (callable(func) and name.startswith("test_") and hasattr(func, "__code__")):
                continue
            wanted = func.__code__.co_varnames[: func.__code__.co_argcount]
            needs_paper = "paper" in wanted or "document_bytes" in wanted
            cases = PAPERS if needs_paper else [""]
            for case in cases:
                label = f"{module_name}::{name}" + (f"[{case}]" if case else "")
                with tempfile.TemporaryDirectory() as tmp:
                    try:
                        func(**_arguments(func, case, Path(tmp)))
                        passed += 1
                    except _Skip:
                        skipped += 1
                    except Exception:
                        failed += 1
                        failures.append((label, traceback.format_exc()))

    for label, tb in failures:
        print(f"\nFAILED {label}\n{tb}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
