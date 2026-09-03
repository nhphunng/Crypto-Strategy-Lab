"""Fix editor-save: serialize a clone WITHOUT the editor UI so reloads never
stack duplicate toolbars (the script runs before trailing saved UI is parsed)."""
import pathlib

P = pathlib.Path(r"F:\D\Uni\YEAR_3\SEM_3\KTPM\Crypto-Strategy-Lab\docs\presentation\crypto-strategy-lab-slides.html")
c = P.read_text(encoding="utf-8")

old = """    setEditing(false);
    var html = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;"""
new = """    setEditing(false);
    // Serialize a clone with the editor UI stripped, so saved files stay clean.
    var root = document.documentElement.cloneNode(true);
    ['.le-toolbar', '.le-hint', '.le-notes', '.le-anno'].forEach(function (sel) {
      var n = root.querySelector(sel);
      if (n) n.remove();
    });
    var html = '<!DOCTYPE html>\\n' + root.outerHTML;"""
assert c.count(old) == 1, "save() serialization line not found"
c = c.replace(old, new)

# Belt-and-suspenders: also dedupe stale UI at DOMContentLoaded (files saved by the buggy version)
old2 = "  setEditing(false);\n})();"
new2 = """  // Also strip any editor UI that finished parsing after this script ran
  // (files saved by the earlier buggy version may contain it at end of body).
  document.addEventListener('DOMContentLoaded', function () {
    ['.le-toolbar', '.le-hint', '.le-notes', '.le-anno'].forEach(function (sel) {
      var all = document.querySelectorAll(sel);
      for (var i = 1; i < all.length; i++) all[i].remove();
    });
  });

  setEditing(false);
})();"""
assert c.count(old2) == 1, "editor IIFE tail not found"
c = c.replace(old2, new2)

P.write_text(c, encoding="utf-8", newline="\n")
print("save-strip patched")
