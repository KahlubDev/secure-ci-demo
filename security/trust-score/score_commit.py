"""
Kinga trust-score check, CI entry point.

Week 1's script scored the whole history at once - fine for exploring data,
wrong for a CI gate. A CI gate has one job: look at the commit that just
landed, decide if it's risky, and pass or fail the build accordingly.

So the shape here is different on purpose:
  - BASELINE = every commit before the one we're checking
  - TARGET   = the commit this workflow run is actually about

This mirrors the real world: a bank doesn't recompute your entire spending
history to flag one transaction, it compares that one transaction against
your established pattern.
"""
import subprocess
import sys
import math
import statistics
from datetime import datetime

# --- reuse Week 1's parsing logic, unchanged - a two-line separator that
# never collides with real commit message text ---
def get_commits(repo_path="."):
    fmt = "%x1e%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
    result = subprocess.run(
        ["git", "log", f"--pretty=format:{fmt}", "--date=iso-strict", "--numstat"],
        cwd=repo_path, capture_output=True, text=True, check=True
    )
    records = result.stdout.split("\x1e")[1:]
    commits = []
    for record in records:
        lines = record.strip("\n").split("\n")
        commit_hash, author, email, date_str, subject = lines[0].split("\x1f")
        additions, deletions = 0, 0
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) == 3:
                add, delete, _ = parts
                additions += int(add) if add.isdigit() else 0
                deletions += int(delete) if delete.isdigit() else 0
        commits.append({
            "hash": commit_hash[:8], "author": author, "email": email,
            "date": date_str, "subject": subject,
            "additions": additions, "deletions": deletions,
        })
    return commits


def circular_hour_stats(hours):
    """Same fix as Week 1: hour-of-day wraps at midnight, so average it
    as an angle on a clock face, not as a plain number."""
    angles = [h / 24 * 2 * math.pi for h in hours]
    mean_x = statistics.mean(math.cos(a) for a in angles)
    mean_y = statistics.mean(math.sin(a) for a in angles)
    mean_angle = math.atan2(mean_y, mean_x)
    mean_hour = (mean_angle / (2 * math.pi) * 24) % 24
    r = math.sqrt(mean_x**2 + mean_y**2)
    stdev_hour = math.sqrt(max(-2 * math.log(r), 0.0001)) / (2 * math.pi) * 24
    return mean_hour, stdev_hour


def hour_distance(h1, h2):
    diff = abs(h1 - h2) % 24
    return min(diff, 24 - diff)


WEIGHTS = {
    "is_new_author": 40,
    "is_odd_hour": 15,
    "is_large_diff": 20,
    "is_short_message": 10,
    "is_weekend": 15,
}

RISK_BANDS = [(70, "HIGH"), (35, "MEDIUM"), (0, "LOW")]


def build_baseline(baseline_commits):
    """Learn 'normal' from every commit before the one we're checking."""
    if len(baseline_commits) < 3:
        # not enough history yet to learn a pattern - fall back to
        # conservative defaults rather than a baseline built on noise
        return {"mean_hour": 12.0, "stdev_hour": 6.0, "diff_threshold": 100}

    hours = []
    for c in baseline_commits:
        dt = datetime.fromisoformat(c["date"])
        hours.append(dt.hour + dt.minute / 60)
    mean_hour, stdev_hour = circular_hour_stats(hours)

    diffs = [c["additions"] + c["deletions"] for c in baseline_commits]
    diff_threshold = max(statistics.median(diffs) * 4, 50)

    return {"mean_hour": mean_hour, "stdev_hour": stdev_hour, "diff_threshold": diff_threshold}


def score_target(target, baseline_commits, baseline_stats):
    dt = datetime.fromisoformat(target["date"])
    hour = dt.hour + dt.minute / 60

    known_authors = {c["author"] for c in baseline_commits}

    features = {
        "is_new_author": target["author"] not in known_authors,
        "is_odd_hour": hour_distance(hour, baseline_stats["mean_hour"]) > 2 * baseline_stats["stdev_hour"],
        "is_large_diff": (target["additions"] + target["deletions"]) > baseline_stats["diff_threshold"],
        "is_short_message": len(target["subject"]) < 10,
        "is_weekend": dt.weekday() >= 5,
    }

    triggered = [name for name, val in features.items() if val]
    score = sum(WEIGHTS[name] for name in triggered)
    band = next(label for threshold, label in RISK_BANDS if score >= threshold)
    return score, band, triggered


if __name__ == "__main__":
    commits = get_commits()
    commits.sort(key=lambda c: c["date"])  # oldest to newest

    if len(commits) < 2:
        print("Not enough history to score yet. Passing by default.")
        sys.exit(0)

    target = commits[-1]              # the commit this run is checking
    baseline_commits = commits[:-1]   # everything before it

    baseline_stats = build_baseline(baseline_commits)
    score, band, triggered = score_target(target, baseline_commits, baseline_stats)

    print(f"Commit:    {target['hash']}  {target['subject']}")
    print(f"Author:    {target['author']}")
    print(f"Score:     {score}")
    print(f"Verdict:   {band}")
    print(f"Triggered: {', '.join(triggered) or 'none'}")

    summary_path = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(f"### Kinga Trust Score\n\n")
            f.write(f"| Field | Value |\n|---|---|\n")
            f.write(f"| Commit | `{target['hash']}` |\n")
            f.write(f"| Score | {score} |\n")
            f.write(f"| Verdict | **{band}** |\n")
            f.write(f"| Triggered | {', '.join(triggered) or 'none'} |\n")

    if band == "HIGH":
        print("\nBlocking: this commit needs manual review before merge.")
        sys.exit(1)   # non-zero exit fails the GitHub Actions job
    else:
        print("\nPassing.")
        sys.exit(0)
