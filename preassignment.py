"""
Issue-Commit Metrics Analyzer — pallets/flask
===============================================
Repo  : https://github.com/pallets/flask
Issues: confirmed closed issues whose IDs appear in commit messages.

Metrics calculated:
  1. Average Unique Files Changed
     = Σ unique files (ADD / MODIFY / DELETE) across matched commits
       ÷ total matched commits

  2. Average DMM Score
     = (Σ dmm_unit_size + Σ dmm_unit_complexity + Σ dmm_unit_interfacing)
       ÷ total matched commits

Run
---
    pip install pydriller
    python preassignment.py
"""


from pydriller import Repository
from pydriller.domain.commit import ModificationType
import re
import sys
from typing import Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_URL = "https://github.com/pallets/flask"

# Closed issues confirmed to be referenced in commit messages
# via "closes #N", "fixes #N", or "#N" patterns in the flask repo
ISSUE_IDS = [
    1151,   # closes #1151 — rework context docs
    1348,   # closes #1348 — session not opened if request has open session
    1433,   # closes #1433 — error handler cache
    1528,   # closes #1528 — session error pops context
    1538,   # closes #1538 — session error pops context
    2205,   # connection reset when posting data
    2267,   # closes #2267 — remove error handler cache
    5774,   # stream_with_context fails inside async views
    5776,   # relax type hint for bytes IO in send_file
    5786,   # follow_redirects session state fix
]

# =============================================================================


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RELEVANT_CHANGE_TYPES = {
    ModificationType.ADD,
    ModificationType.MODIFY,
    ModificationType.DELETE,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_pattern(issue_ids: list) -> re.Pattern:
    """
    Match any of the given issue IDs in a commit message.
    Catches all common referencing styles:
        #42   fixes #42   closes #42   resolves #42   gh-42   references #42
    Also matches bare #N references without any keyword prefix.
    """
    ids_alt = "|".join(str(i) for i in issue_ids)
    return re.compile(
        rf"(?:(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?|ref(?:erences?)?|gh-?)\s*#?|#)"
        rf"(?:{ids_alt})\b",
        re.IGNORECASE,
    )


def safe_float(value) -> Optional[float]:
    """Return value as float, or None if unavailable / NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if f != f else f          # discard NaN
    except (TypeError, ValueError):
        return None


def count_unique_files(commit) -> int:
    """
    Count unique file paths in a commit considering only
    ADD, MODIFY, and DELETE change types.
    """
    paths = set()
    for mf in commit.modified_files:
        if mf.change_type in RELEVANT_CHANGE_TYPES:
            path = mf.new_path or mf.old_path
            if path:
                paths.add(path)
    return len(paths)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze(repo_url: str, issue_ids: list) -> None:
    pattern = build_pattern(issue_ids)

    total_commits        = 0
    total_files          = 0
    sum_unit_size        = 0.0
    sum_unit_complexity  = 0.0
    sum_unit_interfacing = 0.0

    print(f"Scanning repository : {repo_url}")
    print(f"Issue IDs           : {issue_ids}")
    print("Please wait, traversing commit history...\n")

    for commit in Repository(repo_url).traverse_commits():
        if not pattern.search(commit.msg or ""):
            continue

        total_commits        += 1
        total_files          += count_unique_files(commit)
        sum_unit_size        += safe_float(commit.dmm_unit_size)        or 0.0
        sum_unit_complexity  += safe_float(commit.dmm_unit_complexity)  or 0.0
        sum_unit_interfacing += safe_float(commit.dmm_unit_interfacing) or 0.0

    # ------------------------------------------------------------------
    # Guard: nothing matched
    # ------------------------------------------------------------------
    if total_commits == 0:
        print("No commits found referencing the given issue IDs.")
        return

    # ------------------------------------------------------------------
    # Compute averages
    #
    #   avg_files = Σ unique_files_per_commit  /  total_commits
    #
    #   avg_dmm   = (Σ unit_size + Σ unit_complexity + Σ unit_interfacing)
    #               /  total_commits
    # ------------------------------------------------------------------
    avg_files_changed = total_files / total_commits
    avg_dmm           = (sum_unit_size + sum_unit_complexity + sum_unit_interfacing) / total_commits

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    print(f"Total commits analysed          : {total_commits}")
    print(f"Average number of files changed : {avg_files_changed:.4f}")
    print(f"Average DMM metrics             : {avg_dmm:.4f}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        analyze(repo_url=REPO_URL, issue_ids=ISSUE_IDS)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise