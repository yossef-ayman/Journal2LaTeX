import os, sys, zipfile, tempfile, stat
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.utils.filesystem import is_within, safe_join, is_valid_job_id, is_safe_component, UnsafePathError
from app.utils import zip_utils as z

def test_all_security_hardening():
    ok = []
    def check(name, cond):
        ok.append((name, bool(cond)))

    # containment
    root = Path("/data/jobs")
    check("prefix-sibling rejected", not is_within(root, "/data/jobs-evil/x"))
    check("child accepted", is_within(root, "/data/jobs/abc/d"))
    check("parent rejected", not is_within(root, "/data"))

    # job ids
    check("uuid ok", is_valid_job_id("3f2504e0-4f89-11d3-9a0c-0305e82c3301"))
    check("traversal id rejected", not is_valid_job_id("../../etc"))
    check("empty id rejected", not is_valid_job_id(""))

    # components
    check("dotdot component rejected", not is_safe_component(".."))
    check("slash component rejected", not is_safe_component("a/b"))
    check("backslash component rejected", not is_safe_component("a\\b"))
    check("nul component rejected", not is_safe_component("a\x00b"))
    check("normal component ok", is_safe_component("main.tex"))

    try:
        safe_join("/tmp", "..", "etc")
        check("safe_join blocks traversal", False)
    except UnsafePathError:
        check("safe_join blocks traversal", True)

    tmp = Path(tempfile.mkdtemp())

    # --- Zip Slip ---
    evil = tmp / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../escaped.txt", "pwned")
    dest = tmp / "out1"; dest.mkdir()
    try:
        z.extract_zip(evil, dest); check("zip slip blocked", False)
    except z.UnsafeArchiveError:
        check("zip slip blocked", True)
    check("no escaped file written", not (tmp / "escaped.txt").exists())

    # --- absolute member ---
    abz = tmp / "abs.zip"
    with zipfile.ZipFile(abz, "w") as zf:
        zf.writestr("/etc/pwned.txt", "x")
    dest2 = tmp / "out2"; dest2.mkdir()
    try:
        z.extract_zip(abz, dest2); check("absolute member blocked", False)
    except z.UnsafeArchiveError:
        check("absolute member blocked", True)

    # --- symlink member ---
    slz = tmp / "sl.zip"
    with zipfile.ZipFile(slz, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "/etc/passwd")
    dest3 = tmp / "out3"; dest3.mkdir()
    try:
        z.extract_zip(slz, dest3); check("symlink member blocked", False)
    except z.UnsafeArchiveError:
        check("symlink member blocked", True)

    # --- benign archive still extracts ---
    good = tmp / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("a/b/c.txt", "hello")
    dest4 = tmp / "out4"; dest4.mkdir()
    z.extract_zip(good, dest4)
    check("benign extract works", (dest4 / "a/b/c.txt").read_text() == "hello")

    # --- zip_directory does not follow symlinks ---
    src = tmp / "src"; (src / "sub").mkdir(parents=True)
    (src / "main.tex").write_text("x")
    (src / "sub" / "f.sty").write_text("y")
    (src / "main.aux").write_text("junk")
    try:
        os.symlink("/etc/passwd", src / "leak.tex")
        os.symlink("/etc", src / "leakdir")
        has_symlinks = True
    except OSError:
        has_symlinks = False
    out = tmp / "pkg.zip"
    z.zip_directory(src, out, exclude_suffixes={".aux"})
    names = set(zipfile.ZipFile(out).namelist())
    if has_symlinks:
        check("symlink file excluded", "leak.tex" not in names)
        check("symlinked dir excluded", not any(n.startswith("leakdir/") for n in names))
    else:
        check("symlink file excluded", True)
        check("symlinked dir excluded", True)
    check("aux excluded", "main.aux" not in names)
    check("real files included", {"main.tex", "sub/f.sty"} <= names)

    fails = [n for n, c in ok if not c]
    for n, c in ok:
        print(("PASS " if c else "FAIL ") + n)
    print()
    print(f"{len(ok)-len(fails)}/{len(ok)} passed")
    assert not fails, f"Security checks failed: {fails}"

if __name__ == "__main__":
    test_all_security_hardening()
