"""Patch the deck's navigation script so clicks in edit/annotate mode don't flip slides."""
import pathlib

P = pathlib.Path(r"F:\D\Uni\YEAR_3\SEM_3\KTPM\Crypto-Strategy-Lab\docs\presentation\crypto-strategy-lab-slides.html")
c = P.read_text(encoding="utf-8")

old = """      document.querySelector('.deck').addEventListener('click', function (e) {
        if (e.target.closest('a, button, .code-container, .notes-panel')) return;"""
new = """      document.querySelector('.deck').addEventListener('click', function (e) {
        // In Live Editor edit/annotate mode, clicks edit or pin — they must not flip slides.
        if (document.body.classList.contains('editing')) return;
        if (e.target.closest('a, button, .code-container, .notes-panel')) return;"""
assert c.count(old) == 1, "nav click handler not found (already patched?)"
c = c.replace(old, new)
P.write_text(c, encoding="utf-8", newline="\n")
print("nav guard patched")
