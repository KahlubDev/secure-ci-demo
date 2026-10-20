"""
Kinga trust-score check, CI entry point (v2: scores every commit in the change).

Two design rules, both learned from testing v1 against a hidden attack:

1. Score EVERY commit the change introduces, not only the newest one.
   A risky commit buried under clean ones must still be caught.

2. Build the baseline ONLY from history that existed before the change.
   Commits inside the change are untrusted input. If they could shape the
   baseline, an attacker could shift "normal" toward their own behavior.

Commits are selected with git's own range syntax (BASE..HEAD), never by
sorting on dates. Author dates are free text set by the committer, so a
date-based "newest commit" can be steered by the attacker.

In CI, BASE_SHA and HEAD_SHA come from the workflow. Without them the script
falls back to local mode: newest commit vs everything before it.
"""
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime

ZERO_SHA = "0" * 40

WEIGHTS = {
    "is_new_author": 40,
    "is_odd_hour": 15,
    "is_large_diff": 20,
    "is_short_message": 10,
    "is_weekend": 15,
}
# HIGH starts at 60: an unknown author (40) plus one real supporting signal.
# Backtested on 18 real commits: no commit after the first one reaches 60.
RISK_BANDS = [(60, "HIGH"), (35, "MEDIUM"), (0, "LOW")]


def git(args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def get_commits(rev_args):
    # \x1e and \x1f are control characters that cannot appear in commit
    # text, so splitting on them is safe where commas or pipes are not.
    fmt = "%x1e%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
    out = git(["log", "--no-merges", f"--pretty=format:{fmt}",
               "--date=iso-strict", "--numstat", *rev_args])
    commits = []
    for record in out.split("\x1e")[1:]:
        lines = record.strip("\n").split("\n")
        h, author, email, date_str, subject = lines[0].split("\x1f")
        additions = deletions = 0
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) == 3:
                a, d, _ = parts
                additions += int(a) if a.isdigit() else 0
                deletions += int(d) if d.isdigit() else 0
        commits.append({"hash": h[:8], "author": author, "email": email,
                        "date": date_str, "subject": subject,
                        "additions": additions, "deletions": deletions})
    return commits


def circular_hour_stats(hours):
    """Hour of day wraps at midnight, so average it as an angle on a clock."""
    angles = [h / 24 * 2 * math.pi for h in hours]
    mx = statistics.mean(math.cos(a) for a in angles)
    my = statistics.mean(math.sin(a) for a in angles)
    mean_hour = (math.atan2(my, mx) / (2 * math.pi) * 24) % 24
    r = math.sqrt(mx ** 2 + my ** 2)
    stdev = math.sqrt(max(-2 * math.log(r), 0.0001)) / (2 * math.pi) * 24
    return mean_hour, stdev


def hour_distance(h1, h2):
    d = abs(h1 - h2) % 24
    return min(d, 24 - d)


def build_baseline(baseline_commits):
    if len(baseline_commits) < 3:
        # Too little history to learn a pattern. Use conservative defaults.
        return {"mean_hour": 12.0, "stdev_hour": 6.0, "diff_threshold": 100}
    hours = []
    for c in baseline_commits:
        dt = datetime.fromisoformat(c["date"])
        hours.append(dt.hour + dt.minute / 60)
    mean_hour, stdev_hour = circular_hour_stats(hours)
    diffs = [c["additions"] + c["deletions"] for c in baseline_commits]
    return {"mean_hour": mean_hour, "stdev_hour": stdev_hour,
            "diff_threshold": max(statistics.median(diffs) * 4, 50)}


def score_one(c, known_authors, stats):
    dt = datetime.fromisoformat(c["date"])
    hour = dt.hour + dt.minute / 60
    features = {
        "is_new_author": c["author"] not in known_authors,
        "is_odd_hour": hour_distance(hour, stats["mean_hour"]) > 2 * stats["stdev_hour"],
        "is_large_diff": (c["additions"] + c["deletions"]) > stats["diff_threshold"],
        "is_short_message": len(c["subject"]) < 10,
        "is_weekend": dt.weekday() >= 5,
    }
    triggered = [k for k, v in features.items() if v]
    score = sum(WEIGHTS[k] for k in triggered)
    band = next(label for t, label in RISK_BANDS if score >= t)
    return score, band, triggered


def select_commits():
    """Return (targets, baseline, description)."""
    base = os.environ.get("BASE_SHA", "").strip()
    head = os.environ.get("HEAD_SHA", "").strip()

    if base and head and base != ZERO_SHA:
        targets = get_commits([f"{base}..{head}"])
        baseline = get_commits([base])
        return targets, baseline, f"range {base[:8]}..{head[:8]}"

    # Local mode: newest commit against everything before it.
    allc = get_commits([])
    if len(allc) < 2:
        return [], allc, "local (not enough history)"
    return [allc[0]], allc[1:], "local: newest commit vs earlier history"


def main():
    try:
        targets, baseline, desc = select_commits()
    except subprocess.CalledProcessError as e:
        # Fail closed. A security gate that cannot read history must not pass.
        print(f"ERROR: could not read git history: {e.stderr.strip()}")
        print("Failing closed. Check that the checkout uses fetch-depth: 0.")
        return 2

    if not targets:
        print(f"No commits to score ({desc}). Passing.")
        return 0

    stats = build_baseline(baseline)
    known_authors = {c["author"] for c in baseline}

    print(f"Scope:    {desc}")
    print(f"Baseline: {len(baseline)} earlier commits, "
          f"{len(known_authors)} known author(s)")
    print(f"Scoring:  {len(targets)} commit(s)\n")
    print(f"{'hash':<10}{'score':<7}{'verdict':<9}{'triggered':<48}subject")

    results = []
    for c in reversed(targets):  # oldest first for readability
        score, band, triggered = score_one(c, known_authors, stats)
        results.append((c, score, band, triggered))
        print(f"{c['hash']:<10}{score:<7}{band:<9}"
              f"{', '.join(triggered) or 'none':<48}{c['subject'][:40]}")
        if band in ("HIGH", "MEDIUM"):
            level = "error" if band == "HIGH" else "warning"
            print(f"::{level} title=Kinga trust score::{c['hash']} scored "
                  f"{score} ({band}): {', '.join(triggered)}")

    worst = max(results, key=lambda r: r[1])
    overall = worst[2]
    blocked = any(r[2] == "HIGH" for r in results)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("### Kinga Trust Score\n\n")
            f.write(f"Scored {len(targets)} commit(s) against a baseline of "
                    f"{len(baseline)} earlier commits.\n\n")
            f.write("| Commit | Score | Verdict | Triggered |\n|---|---|---|---|\n")
            for c, score, band, trig in results:
                f.write(f"| `{c['hash']}` | {score} | **{band}** | "
                        f"{', '.join(trig) or 'none'} |\n")

    print(f"\nHighest risk: {worst[0]['hash']} scored {worst[1]} ({overall})")
    if blocked:
        print("Blocking: at least one commit is HIGH risk and needs manual review.")
        return 1
    print("Passing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())