import io
import os
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.config import settings
from app.core.rate_limiter import InMemoryRateLimiter
from app.services.template_manager import TemplateManager, TemplateManagerError
from app.compiler.latex_compiler import LatexCompiler


@pytest.fixture
def client():
    return TestClient(app)


def test_security_headers_present(client):
    """Test that critical security headers are attached to API responses."""
    response = client.get("/health")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in headers
    assert "frame-ancestors 'none'" in headers.get("content-security-policy", "")
    assert "permissions-policy" in headers


def test_cors_policy(client):
    """Test that CORS policy properly handles allowed and disallowed origins."""
    # Disallowed origin
    resp_disallowed = client.options(
        "/health",
        headers={
            "Origin": "https://malicious-attacker-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # With origin restriction, access-control-allow-origin should NOT equal the malicious site
    allow_origin = resp_disallowed.headers.get("access-control-allow-origin")
    assert allow_origin != "https://malicious-attacker-site.com"

    # Allowed origin (e.g. localhost:5173)
    resp_allowed = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_template_manager_blocks_forbidden_extensions():
    """Test that TemplateManager blocks dangerous extensions (.ps1, .cmd, .exe, .sh, etc.)."""
    tm = TemplateManager()
    assert tm._is_forbidden_file("script.ps1")
    assert tm._is_forbidden_file("payload.bat")
    assert tm._is_forbidden_file("payload.cmd")
    assert tm._is_forbidden_file("malware.exe")
    assert tm._is_forbidden_file("test.vbs")
    assert tm._is_forbidden_file("app.jar")
    assert tm._is_forbidden_file("script.sh")
    assert tm._is_forbidden_file("nested/path/to/script.py")

    # Safe template files should be allowed
    assert not tm._is_forbidden_file("template.tex")
    assert not tm._is_forbidden_file("custom.cls")
    assert not tm._is_forbidden_file("style.sty")
    assert not tm._is_forbidden_file("ref.bib")
    assert not tm._is_forbidden_file("logo.png")


def test_template_manager_blocks_forbidden_names():
    """Test that TemplateManager blocks dangerous config filenames (latexmkrc, .env, etc.)."""
    tm = TemplateManager()
    assert tm._is_forbidden_file("latexmkrc")
    assert tm._is_forbidden_file(".latexmkrc")
    assert tm._is_forbidden_file(".env")
    assert tm._is_forbidden_file(".bashrc")
    assert tm._is_forbidden_file(".profile")


def test_template_zip_with_forbidden_file_rejected():
    """Test that uploading a template package with an executable or latexmkrc is rejected."""
    tm = TemplateManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "evil_template.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("template.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}")
            zf.writestr("latexmkrc", "system('calc.exe');")

        with pytest.raises(TemplateManagerError) as exc_info:
            tm.save_template_package(zip_path)
        assert "forbidden" in str(exc_info.value).lower()


def test_upload_doc_requires_magic_bytes(client):
    """Test that uploading a fake .doc file without OLE CFBF magic bytes is rejected."""
    fake_doc_bytes = b"This is plain text pretending to be a Word .doc binary file."
    files = {
        "file": ("test.doc", io.BytesIO(fake_doc_bytes), "application/msword")
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "not a valid binary .doc document" in response.json().get("detail", "")


def test_latex_compiler_pdflatex_has_no_shell_escape():
    """Verify that pdflatex command in LatexCompiler always includes -no-shell-escape."""
    compiler = LatexCompiler()
    # Check pdflatex command construction
    import inspect
    source = inspect.getsource(compiler._run_pdflatex)
    assert "-no-shell-escape" in source


def test_latex_compiler_latexmk_has_norc_and_no_shell_escape():
    """Verify that latexmk command in LatexCompiler includes -norc and disables shell escape."""
    compiler = LatexCompiler()
    import inspect
    source = inspect.getsource(compiler.compile_tex)
    assert "-norc" in source
    assert "-no-shell-escape" in source


def test_rate_limiter():
    """Verify that InMemoryRateLimiter accurately enforces request limits."""
    import asyncio

    async def _test():
        limiter = InMemoryRateLimiter(requests_per_minute=5)
        ip = "192.168.1.100"

        # First 5 requests should pass
        for _ in range(5):
            assert await limiter.is_allowed(ip) is True

        # 6th request should be blocked
        assert await limiter.is_allowed(ip) is False

        # Another IP should still be allowed
        assert await limiter.is_allowed("192.168.1.101") is True

    asyncio.run(_test())
