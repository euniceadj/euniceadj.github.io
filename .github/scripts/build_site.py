"""Assemble the published site and add the newest CV as resume.pdf.

Usage: python3 build_site.py <site_dir> <cv_dir> <out_dir>

- Copies the website files (everything except .git and .github) to out_dir.
- Looks in cv_dir for PDFs named like "... (2026 Nov).pdf" (short or full
  month name), ignores every other file, and picks the latest year and month
  from the file names. Upload order does not matter.
- Copies only that one PDF to out_dir/resume.pdf.
- Fills in the date on the homepage resume card and the name of the
  downloaded file.
- Stops with an error (so the live site stays as it is) if no valid CV is
  found or if two CVs share the newest month.
- Never prints the names of the other files in the CV repository.
"""
import html
import re
import shutil
import sys
from pathlib import Path

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
NAME_PATTERN = re.compile(r"\((\d{4})\s+([A-Za-z]+)\.?\)\.pdf$", re.IGNORECASE)


def find_cvs(cv_dir):
    """Return [(year, month, path)] for every PDF that follows the naming convention."""
    found, skipped = [], 0
    for path in sorted(Path(cv_dir).rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix.lower() != ".pdf":
            continue
        match = NAME_PATTERN.search(path.name)
        month = MONTHS.get(match.group(2).lower()) if match else None
        if not match or not month:
            skipped += 1
            continue
        found.append((int(match.group(1)), month, path))
    return found, skipped


def pick_newest(found):
    if not found:
        raise SystemExit("No CV found. Expected a PDF named like '... (2026 Nov).pdf'. "
                         "The live site was left unchanged.")
    newest = max((year, month) for year, month, _ in found)
    matches = [path for year, month, path in found if (year, month) == newest]
    if len(matches) > 1:
        raise SystemExit(f"{len(matches)} CVs are dated {MONTH_NAMES[newest[1] - 1]} {newest[0]}. "
                         "Keep only one per month. The live site was left unchanged.")
    return newest[0], newest[1], matches[0]


def copy_site(site_dir, out_dir):
    site_dir, out_dir = Path(site_dir), Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(site_dir, out_dir, ignore=shutil.ignore_patterns(".git", ".github"))


def fill_in_card(index_path, year, month, filename):
    text = index_path.read_text(encoding="utf-8")
    date_label = f"{MONTH_NAMES[month - 1]} {year}"
    text, n_date = re.subn(r"(<span data-cv-date>)[^<]*(</span>)",
                           lambda m: m.group(1) + date_label + m.group(2), text)
    safe_name = html.escape(filename, quote=True)
    text, n_dl = re.subn(r'download="[^"]*"(\s+data-cv-download)',
                         lambda m: f'download="{safe_name}"' + m.group(1), text)
    if n_date != 1 or n_dl != 1:
        raise SystemExit("Could not find the resume card markers in index.html. "
                         "The live site was left unchanged.")
    index_path.write_text(text, encoding="utf-8")
    return date_label


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    site_dir, cv_dir, out_dir = sys.argv[1:]
    found, skipped = find_cvs(cv_dir)
    year, month, cv_path = pick_newest(found)
    copy_site(site_dir, out_dir)
    shutil.copyfile(cv_path, Path(out_dir) / "resume.pdf")
    label = fill_in_card(Path(out_dir) / "index.html", year, month, cv_path.name)
    print(f"Published CV dated {label} as /resume.pdf "
          f"({len(found)} valid CV file(s) checked, {skipped} other PDF(s) skipped).")


if __name__ == "__main__":
    main()
