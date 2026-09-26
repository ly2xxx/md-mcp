#!/usr/bin/env python3
"""The design half of an AI-native SDLC as one GitHub Actions run, plus the
checks for the human-built half.

    sdlc_stage.py resolve        pick the feature folder, its branch and the first stage
    sdlc_stage.py stage NAME     write intent.md, spec.md or plan.md with Ollama Cloud
                                 and push it to the feature branch
    sdlc_stage.py verify         check the built branch against plan.md's phases
    sdlc_stage.py pr             open the pull request for the feature branch

Between stages the workflow waits on a GitHub environment with required
reviewers: a person reads the artifact on the feature branch, edits it there
if it needs changing, and approves. People build the code phase by phase from
plan.md (with Claude Code or by hand); `verify` then checks the branch before
the pull request is opened. It runs locally too:

    python .github/actions/sdlc-stage/sdlc_stage.py verify --feature 002-x --phase 1

Standard library only, so a runner needs nothing but python3, git and gh.
"""
import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ACTION_DIR = Path(__file__).resolve().parent
STAGES = ("intent", "spec", "plan")
FEATURE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
# The markers deterministic-coding's phase_check.py reads, so the same plan
# works with that script locally.
MARKER = re.compile(r"<!--\s*(?P<key>phase|targets|frozen)\s*:\s*(?P<value>.*?)\s*-->", re.IGNORECASE)


def env(name, default=""):
    return os.environ.get(name, "").strip() or default


def fail(message):
    print(f"::error::{message}", flush=True)
    sys.exit(1)


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        fail(f"{' '.join(cmd[:3])} exited {r.returncode}: {r.stderr.strip()[-2000:]}")
    return r.stdout.strip()


def git(*args, check=True):
    return sh("git", *args, check=check)


def set_output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")


def step_summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def repo_url(*parts):
    base = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{env('GITHUB_REPOSITORY')}"
    return "/".join([base, *parts])


# ---------------------------------------------------------------- model call

def _stream(req, model, deadline):
    """Read one streamed /api/chat reply. Streaming keeps bytes flowing while a
    model thinks, so no proxy drops the connection as idle, and it lets the log
    show progress instead of minutes of silence."""
    content, thinking, last_note = [], 0, time.monotonic()
    # The timeout is per socket read: the longest silence tolerated between chunks.
    with urllib.request.urlopen(req, timeout=int(env("OLLAMA_IDLE_TIMEOUT", "300"))) as resp:
        for line in resp:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise RuntimeError(chunk["error"])
            message = chunk.get("message", {})
            content.append(message.get("content", ""))
            thinking += len(message.get("thinking", ""))
            now = time.monotonic()
            if now > deadline:
                raise TimeoutError(f"no complete answer within {env('OLLAMA_TIMEOUT', '1200')}s")
            if now - last_note > 30:
                print(f"  {model}: {thinking} thinking and {sum(map(len, content))} answer characters so far",
                      flush=True)
                last_note = now
            if chunk.get("done"):
                return "".join(content)
    raise http.client.IncompleteRead(b"", None)


def chat(model, prompt, want_json=False):
    payload = {"model": model, "stream": True,
               "messages": [{"role": "user", "content": prompt}]}
    if want_json:
        payload["format"] = "json"
    think = env("OLLAMA_THINK").lower()
    if think:
        # true/false, or low/medium/high for models that take a level.
        payload["think"] = {"true": True, "false": False}.get(think, think)
    req = urllib.request.Request(
        env("OLLAMA_HOST", "https://ollama.com").rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + env("OLLAMA_API_KEY"),
                 "Content-Type": "application/json"})
    deadline = time.monotonic() + int(env("OLLAMA_TIMEOUT", "1200"))
    print(f"Calling {model}" + (f" (think={think})" if think else ""), flush=True)
    for attempt in (1, 2):
        try:
            content = _stream(req, model, deadline)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            if attempt == 2 or e.code < 500:
                fail(f"Ollama returned HTTP {e.code} for {model}: {body}")
        except TimeoutError as e:
            fail(f"{model}: {e}. Try a faster model or OLLAMA_THINK=false.")
        except (urllib.error.URLError, OSError, http.client.HTTPException, RuntimeError, ValueError) as e:
            if attempt == 2 or time.monotonic() > deadline:
                fail(f"Ollama request to {model} failed: {e}")
        print(f"::warning::Ollama request to {model} failed; retrying once.", flush=True)
    # Some models put their reasoning inline instead of in the thinking field.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        fail(f"{model} returned no answer")
    return content


def unfence(text):
    """Drop a single code fence wrapped around the whole answer."""
    m = re.fullmatch(r"```[a-zA-Z]*\n(.*)\n```", text.strip(), flags=re.DOTALL)
    return m.group(1) if m else text


# ---------------------------------------------------------------- repository context

def tracked_files():
    return set(git("ls-files").splitlines())


def repo_tree(files, limit=400):
    shown = sorted(f for f in files if not f.startswith(("archive/", "image/", "demo/")))
    extra = len(shown) - limit
    return "\n".join(shown[:limit]) + (f"\n... and {extra} more" if extra > 0 else "")


def mentioned_files(text, files):
    """Tracked files that `text` names by path or by unique basename."""
    by_name = {}
    for f in files:
        by_name.setdefault(Path(f).name, []).append(f)
    hits = set()
    for token in set(re.findall(r"[\w./-]+\.\w+", text)):
        token = token.strip("./")
        if token in files:
            hits.add(token)
        elif len(by_name.get(token, [])) == 1:
            hits.add(by_name[token][0])
    return sorted(hits)


def file_block(path, budget):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if len(text) > budget:
        text = text[:budget] + "\n... (truncated)"
    return f"### {path}\n```\n{text}\n```\n"


# ---------------------------------------------------------------- plan.md

def glob_to_regex(pattern):
    """phase_check.py's glob rules: `*` stops at `/`, `**` crosses it."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append(r"(?:[^/]+/)*"); i += 3
        elif pattern.startswith("**", i):
            out.append(r".*"); i += 2
        elif pattern[i] == "*":
            out.append(r"[^/]*"); i += 1
        elif pattern[i] == "?":
            out.append(r"[^/]"); i += 1
        else:
            out.append(re.escape(pattern[i])); i += 1
    return re.compile("".join(out) + r"\Z")


def matches_any(path, patterns):
    return any(glob_to_regex(p).match(path) for p in patterns)


def parse_phases(text):
    """Each `## Phase` section: its id, title, target and frozen globs, Definition
    of Done checkboxes and the commands in its Verify block."""
    phases = []
    sections = re.split(r"^## (?=Phase\b)", text, flags=re.MULTILINE)[1:]
    for section in sections:
        title = section.splitlines()[0].strip()
        marks = {"phase": "", "targets": [], "frozen": []}
        for m in MARKER.finditer(section):
            key, value = m.group("key").lower(), m.group("value")
            marks[key] = value.strip() if key == "phase" else [p.strip() for p in value.split(",") if p.strip()]
        verify = re.search(r"\*\*Verify[^\n]*\n+```[a-z]*\n(.*?)\n```", section, flags=re.DOTALL | re.IGNORECASE)
        phases.append({
            "id": marks["phase"], "title": title, "targets": marks["targets"], "frozen": marks["frozen"],
            "dod": re.findall(r"^- \[[ xX]\] (.+)$", section, flags=re.MULTILINE),
            "verify": verify.group(1).strip() if verify else "",
        })
    return phases


def bullets(markdown, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", markdown, flags=re.MULTILINE | re.DOTALL)
    return re.findall(r"^\s*[-*] (.+)$", m.group(1), flags=re.MULTILINE) if m else []


def plan_problems(plan, intent):
    phases = parse_phases(plan)
    if not phases:
        return ["No `## Phase N: ...` sections."]
    problems = []
    for p in phases:
        name = f"'{p['title']}'"
        if not p["id"]:
            problems.append(f"{name} has no <!-- phase: N --> marker.")
        if not p["targets"]:
            problems.append(f"{name} has no <!-- targets: ... --> marker.")
        if not p["dod"]:
            problems.append(f"{name} has no Definition of done checklist (- [ ] ...).")
        if not p["verify"]:
            problems.append(f"{name} has no **Verify:** block with a fenced command.")
    rows = re.search(r"^## Coverage\s*\n(.*?)(?=^## |\Z)", plan, flags=re.MULTILINE | re.DOTALL)
    wanted = len(bullets(intent, "Done when"))
    got = len([r for r in rows.group(1).splitlines() if r.startswith("|")]) - 2 if rows else 0
    if not rows:
        problems.append("No `## Coverage` table mapping intent.md's Done-when items to phases.")
    elif got < wanted:
        problems.append(f"The Coverage table has {got} rows but intent.md has {wanted} Done-when items.")
    return problems


# ---------------------------------------------------------------- branches

def branch_for(feature):
    return f"feature/{feature}"


def remote_has(branch):
    return bool(git("ls-remote", "--heads", "origin", branch))


def use_feature_branch(branch):
    """Check out the feature branch, creating it from the current commit if new.
    Called after the approval gate, so a person's edits on the branch are in."""
    if remote_has(branch):
        git("fetch", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
        git("checkout", "-q", "-B", branch, f"origin/{branch}")
    else:
        git("checkout", "-q", "-B", branch)


def new_feature_name(features_dir, idea):
    """NNN-slug-of-the-idea, numbered after the highest feature on the base or on
    any feature/ branch, so two ideas in flight don't share a number."""
    root = Path(features_dir)
    names = [d.name for d in root.iterdir()] if root.is_dir() else []
    names += [ref.rsplit("/", 1)[-1] for ref in git("ls-remote", "--heads", "origin", "feature/*").split()]
    numbers = [int(m.group(1)) for n in names if (m := re.match(r"(\d{3})-", n))]
    slug = "-".join(re.findall(r"[a-z0-9]+", idea.lower())[:6])[:40].strip("-") or "feature"
    return f"{max(numbers, default=0) + 1:03d}-{slug}"


# ---------------------------------------------------------------- resolve

def resolve(args):
    idea, start = env("SDLC_IDEA"), env("SDLC_START", "auto")
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    if start not in ("auto", "intent", "spec", "plan", "build"):
        fail(f"Unknown start stage: {start}")
    if idea and start not in ("auto", "intent"):
        fail("An idea starts at the intent stage. Leave start on auto or intent.")
    if start == "intent" and not idea:
        fail("The intent stage needs an idea.")
    feature = env("SDLC_FEATURE")
    if not feature:
        if not idea:
            fail("Give an idea to start a new feature, or name an existing feature folder.")
        feature = new_feature_name(features_dir, idea)
    if not FEATURE_NAME.fullmatch(feature):
        fail(f"Bad feature name '{feature}': use lowercase letters, digits and hyphens.")
    branch = branch_for(feature)
    use_feature_branch(branch)
    folder = Path(features_dir, feature)
    have = {s: (folder / f"{s}.md").exists() for s in STAGES}
    if start == "auto":
        start = "intent" if idea else next((s for s in STAGES if not have[s]), "build")
    if start != "intent" and not have["intent"]:
        fail(f"{folder}/intent.md doesn't exist on {branch} or the base. Start with an idea.")
    if start == "plan" and not have["spec"]:
        fail(f"{folder}/spec.md doesn't exist yet. Start at spec.")
    if start == "build" and not have["plan"]:
        fail(f"{folder}/plan.md doesn't exist yet. Start at plan.")
    order = ("intent", "spec", "plan", "build")
    runs = {s: order.index(s) >= order.index(start) for s in STAGES}
    if start == "intent" and have["intent"]:
        later = [f"{s}.md" for s in ("spec", "plan") if have[s]]
        print(f"::warning::{feature} already has an intent.md. This run revises it"
              + (f" and then regenerates {', '.join(later)}." if later else "."))
    print(f"Feature {feature} on {branch}, starting at {start}.")
    step_summary(f"**Feature** `{feature}` · **branch** [`{branch}`]({repo_url('tree', branch)}) · "
                 f"**starts at** {start}")
    set_output(feature=feature, branch=branch, start=start, **{s: str(runs[s]).lower() for s in STAGES})


# ---------------------------------------------------------------- stage

def header(stage, model, sources):
    return (f"<!-- sdlc stage={stage} model={model} "
            f"from={','.join(sources)}@{git('rev-parse', '--short', 'HEAD')} -->\n")


def prompt_parts(stage, folder, files, budget, idea):
    parts = [(ACTION_DIR / "prompts" / f"{stage}.md").read_text(encoding="utf-8")]
    sources = []
    if stage == "intent":
        parts += [f"## Owner\n@{env('ACTOR', 'unknown')}", "## The idea\n" + idea]
        sources.append("idea")
        if (folder / "intent.md").exists():
            parts.append("## Existing intent.md (revise this; keep what the idea does not change)\n"
                         + (folder / "intent.md").read_text(encoding="utf-8"))
            sources.append("intent.md")
    else:
        for name in ("intent", "spec")[: STAGES.index(stage)]:
            parts.append(f"## {name}.md\n" + (folder / f"{name}.md").read_text(encoding="utf-8"))
            sources.append(f"{name}.md")
    named = mentioned_files("\n".join(parts[1:]), files)
    parts.append("## Repository files\n" + repo_tree(files))
    if Path("README.md").exists():
        parts.append("## README.md (start)\n" + Path("README.md").read_text(encoding="utf-8")[:4000])
    used = sum(map(len, parts))
    for path in named:
        if path.startswith(str(folder)) or budget - used < 1000:
            continue
        block = file_block(path, budget - used)
        parts.append(block)
        used += len(block)
    return parts, sources


def stage(args):
    name = args.name
    if name not in STAGES:
        fail(f"Unknown stage {name}")
    feature = env("SDLC_FEATURE") or fail("SDLC_FEATURE is not set")
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    branch = branch_for(feature)
    use_feature_branch(branch)
    folder = Path(features_dir, feature)
    files = tracked_files()
    model = env("OLLAMA_MODEL", "deepseek-v4-flash:cloud")
    parts, sources = prompt_parts(name, folder, files, int(env("MAX_CONTEXT_CHARS", "60000")), env("SDLC_IDEA"))
    print(f"Writing {name}.md for {feature}", flush=True)
    text = unfence(chat(model, "\n\n".join(parts)))
    problems = []
    if name == "plan":
        intent = (folder / "intent.md").read_text(encoding="utf-8")
        problems = plan_problems(text, intent)
        if problems:
            print("::warning::The plan is incomplete; asking once more: " + " ".join(problems), flush=True)
            retry = ("\n\n## Your previous plan was rejected\n" + "\n".join(f"- {p}" for p in problems)
                     + "\n\n## Your previous plan\n" + text + "\n\nWrite the whole plan again, fixed.")
            text = unfence(chat(model, "\n\n".join(parts) + retry))
            problems = plan_problems(text, intent)

    path = folder / f"{name}.md"
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(header(name, model, sources) + text + "\n", encoding="utf-8")
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898283+github-actions[bot]@users.noreply.github.com")
    git("add", str(path))
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        print(f"{path} is unchanged.")
    else:
        git("commit", "-q", "-m", f"sdlc({feature}): {name}\n\nWritten by the {name} stage with {model}.")
        git("push", "-q", "origin", f"HEAD:refs/heads/{branch}")

    view, edit = repo_url("blob", branch, str(path)), repo_url("edit", branch, str(path))
    summary = [f"## {name}.md is ready for review", "",
               f"[View]({view}) · [Edit on the branch]({edit}) · model `{model}`", "",
               "Read it, edit it on the branch if it needs changing, then approve the next "
               "**Review** job (Review deployments). Rejecting stops the run.", ""]
    if problems:
        summary += ["> [!WARNING]", "> The plan still has problems. Fix them on the branch before approving:"]
        summary += [f"> - {p}" for p in problems] + [""]
        for p in problems:
            print(f"::warning::{p}")
    step_summary("\n".join(summary) + "\n---\n\n" + path.read_text(encoding="utf-8"))
    set_output(path=str(path))


# ---------------------------------------------------------------- verify

def changed_since(base, include_worktree):
    if include_worktree:
        tracked = git("diff", "--name-only", "HEAD").split()
        untracked = git("ls-files", "--others", "--exclude-standard").split()
        return sorted(set(tracked) | set(untracked))
    return sorted(set(git("diff", "--name-only", f"{base}...HEAD").split()))


def run_check(command, timeout=900):
    try:
        r = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", command], capture_output=True, text=True,
                           timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[-4000:]
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"


def verify(args):
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    feature = args.feature or env("SDLC_FEATURE") or fail("Name the feature (--feature).")
    folder = Path(features_dir, feature)
    plan_path = folder / "plan.md"
    if not plan_path.exists():
        fail(f"{plan_path} doesn't exist")
    phases = parse_phases(plan_path.read_text(encoding="utf-8"))
    if args.phase:
        phases = [p for p in phases if p["id"] == args.phase] or fail(f"plan.md has no phase {args.phase}")
    base = args.base or env("BASE_REF")
    # One phase is checked against uncommitted work, like phase_check.py; the
    # whole feature against everything the branch changed since the base.
    if args.phase:
        changed, against = changed_since(None, True), "uncommitted changes"
    else:
        if not base:
            fail("Give --base (the branch the feature goes into).")
        git("fetch", "-q", "origin", base, check=False)
        ref = f"origin/{base}" if git("rev-parse", "--verify", "-q", f"origin/{base}", check=False) else base
        changed, against = changed_since(ref, False), f"changes since `{base}`"
    changed = [p for p in changed if not p.startswith(str(folder) + "/")]
    targets = [t for p in phases for t in p["targets"]]
    frozen = [f for p in phases for f in p["frozen"]]
    frozen_hit = [p for p in changed if matches_any(p, frozen)]
    outside = [p for p in changed if not matches_any(p, targets) and p not in frozen_hit]

    rows, ok = [], True
    report = [f"# Verification: {feature}" + (f", phase {args.phase}" if args.phase else ""), ""]
    if not changed:
        report.append(f"> [!WARNING]\n> No code changed ({against}). Nothing has been built yet.\n")
        ok = False
    report += [f"**Scope** ({against}): {len(changed)} file(s) changed. "
               + ("All inside the plan's targets." if not outside else f"**{len(outside)} outside the plan:** "
                  + ", ".join(f"`{p}`" for p in outside)),
               f"**Frozen files:** " + ("none touched." if not frozen_hit else "**modified:** "
                                         + ", ".join(f"`{p}`" for p in frozen_hit)), ""]
    ok = ok and not outside and not frozen_hit
    test_command = args.test_command or env("TEST_COMMAND")
    if test_command:
        code, out = run_check(test_command)
        rows.append(("Whole test suite", test_command, code, out))
    for p in phases:
        if p["verify"]:
            code, out = run_check(p["verify"])
            rows.append((f"Phase {p['id']}: {p['title'].split(':', 1)[-1].strip()}", p["verify"], code, out))
        else:
            rows.append((f"Phase {p['id']}", "(no Verify block)", 1, "plan.md gives this phase no Verify command"))
    report += ["| Check | Result |", "| :-- | :-- |"]
    for name, _, code, _ in rows:
        report.append(f"| {name} | {'✅ passed' if code == 0 else f'❌ exit {code}'} |")
        ok = ok and code == 0
    report.append("")
    for name, command, code, out in rows:
        report += [f"<details><summary>{name}: {'passed' if code == 0 else 'failed'}</summary>", "",
                   "```bash", command, "```", "```", out.strip(), "```", "</details>", ""]
    report.insert(1, f"**Result: {'PASSED' if ok else 'FAILED'}**\n")
    text = "\n".join(report)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    step_summary(text)
    print(text)
    set_output(passed=str(ok).lower())
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------- pr

def pr(args):
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    feature = env("SDLC_FEATURE") or fail("SDLC_FEATURE is not set")
    base = env("BASE_REF") or fail("BASE_REF is not set")
    branch = branch_for(feature)
    folder = Path(features_dir, feature)
    passed = env("VERIFY_PASSED") == "true"
    intent = (folder / "intent.md").read_text(encoding="utf-8")
    title_m = re.search(r"^# Intent:\s*(.+)$", intent, flags=re.MULTILINE)
    title = f"{feature}: {title_m.group(1).strip() if title_m else 'feature'}"
    phases = parse_phases((folder / "plan.md").read_text(encoding="utf-8"))
    report_path = Path(args.report) if args.report else None
    report = report_path.read_text(encoding="utf-8") if report_path and report_path.exists() else \
        "_The verification report is missing._"
    links = " · ".join(f"[{n}.md]({repo_url('blob', branch, str(folder / (n + '.md')))})" for n in STAGES)
    body = [f"Built from {links}, each approved in the SDLC Pipeline run.", "",
            ("Verification **passed**. Review the code, then merge." if passed else
             "Verification **failed**, so this is a draft. Push fixes to "
             f"`{branch}` and re-run the failed jobs."), "", "## Phases"]
    for p in phases:
        body.append(f"- [{'x' if passed else ' '}] **Phase {p['id']}**: {p['title'].split(':', 1)[-1].strip()}")
        body += [f"  - {d}" for d in p["dod"]]
    body += ["", report]
    body_text = "\n".join(body)[:60000]
    existing = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url", "--jq", ".[0].url")
    if existing:
        sh("gh", "pr", "edit", existing, "--title", title, "--body", body_text)
        if passed:
            sh("gh", "pr", "ready", existing, check=False)
        url = existing
    else:
        cmd = ["gh", "pr", "create", "--base", base, "--head", branch, "--title", title, "--body", body_text]
        url = sh(*cmd, *([] if passed else ["--draft"]))
    print(f"Pull request: {url}")
    step_summary(f"Pull request: {url}")
    set_output(pr=url)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resolve")
    s = sub.add_parser("stage")
    s.add_argument("name", choices=STAGES)
    v = sub.add_parser("verify")
    v.add_argument("--feature")
    v.add_argument("--phase", help="check one phase against uncommitted changes")
    v.add_argument("--base", help="branch the feature goes into (whole-feature check)")
    v.add_argument("--test-command")
    v.add_argument("--report", help="also write the report to this file")
    p = sub.add_parser("pr")
    p.add_argument("--report")
    args = ap.parse_args()
    {"resolve": resolve, "stage": stage, "verify": verify, "pr": pr}[args.cmd](args)


if __name__ == "__main__":
    main()
