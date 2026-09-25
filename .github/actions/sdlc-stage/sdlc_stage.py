#!/usr/bin/env python3
"""One stage of the intent -> spec -> plan -> build pipeline, driven by Ollama Cloud.

    sdlc_stage.py generate   pick the feature and stage, call the model, and (build)
                             apply its files and run the tests; results go to SDLC_OUT
    sdlc_stage.py propose    copy SDLC_OUT into the checkout and open a pull request

The two halves run in separate jobs on purpose. `generate` executes model-written
code (the tests), so its job holds a read-only token. `propose` holds the write
token and never executes anything from the model: it re-validates every path and
copies files.

Standard library only, so the runner needs nothing but python3, git and gh.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ACTION_DIR = Path(__file__).resolve().parent
STAGES = ("spec", "plan", "build")
# The artifact each stage writes; a feature's next stage is the first one missing.
ARTIFACT = {"spec": "spec.md", "plan": "plan.md", "build": "build-report.md"}
NEXT_ON_MERGE = {"spec": "plan", "plan": "build", "build": None}


def env(name, default=""):
    return os.environ.get(name, "").strip() or default


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        fail(f"{' '.join(cmd[:3])} exited {r.returncode}: {r.stderr.strip()[-2000:]}")
    return r.stdout.strip()


def git(*args):
    return sh("git", *args)


def set_output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        for key, value in values.items():
            fh.write(f"{key}={value}\n")


def step_summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def fail(message):
    print(f"::error::{message}")
    sys.exit(1)


# ---------------------------------------------------------------- path rules

def is_test_file(path):
    name = Path(path).name
    return (name.startswith("test_") or name.endswith("_test.py")
            or "tests" in Path(path).parts)


def path_problem(path, existing, allowed=None):
    """Why the model may not write `path`, or None. `existing` is the set of files
    tracked at the base commit; `allowed` is the plan's file list, if any."""
    p = Path(path)
    if not path or p.is_absolute() or ".." in p.parts or path != p.as_posix():
        return "not a clean relative path"
    if p.parts[0] in (".git", ".github"):
        return "the pipeline may not change .git or .github"
    if allowed is not None and path not in allowed:
        return "not in the plan's Files list"
    if path in existing and is_test_file(path):
        return "existing tests are frozen; add a new test file instead"
    return None


# ---------------------------------------------------------------- model call

def chat(model, prompt, want_json=False):
    payload = {"model": model, "stream": False,
               "messages": [{"role": "user", "content": prompt}]}
    if want_json:
        payload["format"] = "json"
    req = urllib.request.Request(
        env("OLLAMA_HOST", "https://ollama.com").rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + env("OLLAMA_API_KEY"),
                 "Content-Type": "application/json"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                content = json.load(resp).get("message", {}).get("content", "")
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            if attempt == 2 or e.code < 500:
                fail(f"Ollama returned HTTP {e.code}: {body}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                fail(f"Ollama request failed: {e}")
    # Reasoning models can put their thinking inline; it is not part of the answer.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        fail("Ollama returned no content")
    return content


def unfence(text):
    """Drop a single code fence wrapped around the whole answer."""
    m = re.fullmatch(r"```[a-zA-Z]*\n(.*)\n```", text.strip(), flags=re.DOTALL)
    return m.group(1) if m else text


# ---------------------------------------------------------------- context

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
    hits = []
    for token in set(re.findall(r"[\w./-]+\.\w+", text)):
        token = token.strip("./")
        if token in files:
            hits.append(token)
        elif len(by_name.get(token, [])) == 1:
            hits.append(by_name[token][0])
    return sorted(set(hits))


def file_block(path, budget):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if len(text) > budget:
        text = text[:budget] + "\n... (truncated)"
    return f"### {path}\n```\n{text}\n```\n"


def plan_files(plan_text):
    """The `## Files` section of plan.md: one `- path` per line."""
    m = re.search(r"^## Files\s*\n(.*?)(?=^## |\Z)", plan_text, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return []
    return [line.strip()[2:].strip().strip("`")
            for line in m.group(1).splitlines() if line.strip().startswith("- ")]


# ---------------------------------------------------------------- generate

def pick_feature(features_dir):
    feature = env("SDLC_FEATURE")
    if feature:
        return feature
    before, after = env("PUSH_BEFORE"), env("PUSH_AFTER", "HEAD")
    if not before or set(before) == {"0"}:
        changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", after)
    else:
        changed = git("diff", "--name-only", before, after)
    names = sorted({Path(p).parts[len(Path(features_dir).parts)]
                    for p in changed.splitlines()
                    if p.startswith(features_dir + "/") and Path(p).name in ("intent.md", "spec.md", "plan.md")})
    if len(names) > 1:
        print(f"::warning::Several features changed ({', '.join(names)}); running {names[0]} only.")
    return names[0] if names else ""


def pick_stage(feature_path):
    stage = env("SDLC_STAGE", "next")
    if stage in STAGES:
        return stage
    for s in STAGES:
        if not (feature_path / ARTIFACT[s]).exists():
            return s
    return ""


def header(stage, model, sources):
    head = git("rev-parse", "--short", "HEAD")
    return f"<!-- sdlc stage={stage} model={model} from={','.join(sources)}@{head} -->\n"


def run_doc_stage(stage, feature_path, files, budget):
    model = env("OLLAMA_MODEL", "deepseek-v4-flash:cloud")
    intent = (feature_path / "intent.md").read_text(encoding="utf-8")
    parts = [(ACTION_DIR / "prompts" / f"{stage}.md").read_text(encoding="utf-8"),
             "## intent.md\n" + intent]
    sources = ["intent.md"]
    if stage == "plan":
        parts.append("## spec.md\n" + (feature_path / "spec.md").read_text(encoding="utf-8"))
        sources.append("spec.md")
    # Source files the intent or spec names, so the model sees the code it designs against.
    named = mentioned_files("\n".join(parts[1:]), files)
    parts.append("## Repository files\n" + repo_tree(files))
    readme = Path("README.md")
    if readme.exists():
        parts.append("## README.md (start)\n" + readme.read_text(encoding="utf-8")[:4000])
    used = sum(map(len, parts))
    for path in named:
        if path.startswith(str(feature_path)):
            continue
        if budget - used < 1000:
            break
        block = file_block(path, budget - used)
        parts.append(block)
        used += len(block)
    text = unfence(chat(model, "\n\n".join(parts)))
    if stage == "plan":
        listed = plan_files(text)
        if not listed:
            fail("The plan has no '## Files' section, so the build stage would not know what it may change.")
        blocked = [f"{p} ({why})" for p in listed if (why := path_problem(p, files))]
        if blocked:
            fail("The plan lists files the build may not touch: " + "; ".join(blocked))
    return {ARTIFACT[stage]: header(stage, model, sources) + text + "\n"}, "n/a", model


def run_tests(command):
    # Model-written code runs here. Hand it nothing secret.
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CI", "RUNNER_TEMP")
    clean = {k: os.environ[k] for k in keep if k in os.environ}
    try:
        r = subprocess.run(["bash", "-c", command], capture_output=True, text=True,
                           env=clean, timeout=900)
        code, out = r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        code, out = 124, "test command timed out after 15 minutes"
    if code == 5:
        out += "\npytest collected no tests. An empty suite is a failure, not a pass."
    return code, out


def run_build(feature_path, files, budget):
    model = env("OLLAMA_BUILD_MODEL", "qwen3.5:cloud")
    test_command = env("TEST_COMMAND")
    if not test_command:
        fail("The build stage needs a test-command.")
    intent = (feature_path / "intent.md").read_text(encoding="utf-8")
    spec = (feature_path / "spec.md").read_text(encoding="utf-8")
    plan = (feature_path / "plan.md").read_text(encoding="utf-8")
    allowed = plan_files(plan)
    if not allowed:
        fail("plan.md has no '## Files' section.")
    # Checked again here: a person may have edited plan.md on the plan PR.
    blocked = [f"{p} ({why})" for p in allowed if (why := path_problem(p, files))]
    if blocked:
        fail("The plan lists files the build may not touch: " + "; ".join(blocked))

    setup = env("SETUP_COMMAND")
    if setup:
        r = subprocess.run(["bash", "-c", setup], text=True)
        if r.returncode:
            fail(f"setup-command exited {r.returncode}")

    base = [(ACTION_DIR / "prompts" / "build.md").read_text(encoding="utf-8"),
            "## intent.md\n" + intent, "## spec.md\n" + spec, "## plan.md\n" + plan]
    used = sum(map(len, base))
    for path in allowed:
        if path in files:
            block = file_block(path, max(budget - used, 2000))
            base.append(block)
            used += len(block)
        else:
            base.append(f"### {path}\n(new file)\n")

    attempts, written, feedback = [], {}, ""
    for n in range(1, int(env("MAX_ATTEMPTS", "2")) + 1):
        raw = chat(model, "\n\n".join(base) + feedback, want_json=True)
        try:
            answer = json.loads(unfence(raw))
            changes = answer["files"]
            assert isinstance(changes, list) and changes
        except (ValueError, KeyError, TypeError, AssertionError):
            attempts.append((n, "invalid", "The answer was not JSON with a non-empty 'files' list."))
            feedback = ("\n\n## Your previous answer was rejected\nIt was not JSON of the form "
                        '{"files": [{"path": "...", "content": "..."}], "notes": "..."}. Answer with that JSON only.')
            continue
        rejected = []
        for change in changes:
            path, content = str(change.get("path", "")), change.get("content")
            why = path_problem(path, files, allowed) or (None if isinstance(content, str) else "no content")
            if why:
                rejected.append(f"{path}: {why}")
                continue
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            written[path] = content
        code, out = run_tests(test_command)
        tail = out[-6000:]
        verdict = "passed" if code == 0 and not rejected else "failed"
        attempts.append((n, verdict, "\n".join(rejected) + ("\n" if rejected else "") + tail))
        if verdict == "passed":
            break
        current = "".join(file_block(p, 20000) for p in sorted(written))
        feedback = ("\n\n## Your previous attempt failed\n"
                    + ("Rejected files:\n" + "\n".join(rejected) + "\n\n" if rejected else "")
                    + f"Test command exit code {code}. Output (end):\n```\n{tail}\n```\n\n"
                    + "## The files as they are now\n" + current
                    + "\nFix the cause. Return the same JSON shape with complete file contents.")

    gate = attempts[-1][1] if attempts else "failed"
    gate = "passed" if gate == "passed" else "failed"
    report = [header("build", model, ["intent.md", "spec.md", "plan.md"]),
              f"# Build report: {feature_path.name}\n",
              f"**Gate: {gate.upper()}** after {len(attempts)} attempt(s). "
              f"The gate is the exit code of `{test_command}`, never the model's opinion.\n",
              "## Files written\n" + ("\n".join(f"- `{p}`" for p in sorted(written)) or "_none_") + "\n"]
    for n, verdict, detail in attempts:
        report.append(f"## Attempt {n}: {verdict}\n\n<details><summary>Output</summary>\n\n```\n{detail}\n```\n</details>\n")
    out = dict(written)
    out[ARTIFACT["build"]] = "\n".join(report)
    return out, gate, model


def generate():
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    out_dir = Path(env("SDLC_OUT") or fail("SDLC_OUT is not set"))
    feature = pick_feature(features_dir)
    if not feature:
        print("No feature artifact changed; nothing to do.")
        return set_output(stage="", feature="")
    if "/" in feature or feature.startswith("."):
        fail(f"Bad feature name: {feature}")
    feature_path = Path(features_dir) / feature
    if not (feature_path / "intent.md").exists():
        fail(f"{feature_path}/intent.md does not exist")
    stage = pick_stage(feature_path)
    if not stage:
        print(f"{feature} already has every artifact; nothing to do.")
        return set_output(stage="", feature=feature)
    needed = {"plan": ["spec.md"], "build": ["spec.md", "plan.md"]}.get(stage, [])
    missing = [n for n in needed if not (feature_path / n).exists()]
    if missing:
        fail(f"The {stage} stage needs {', '.join(missing)} in {feature_path}")

    files = tracked_files()
    budget = int(env("MAX_CONTEXT_CHARS", "60000"))
    print(f"Running the {stage} stage for {feature}")
    if stage == "build":
        produced, gate, model = run_build(feature_path, files, budget)
    else:
        produced, gate, model = run_doc_stage(stage, feature_path, files, budget)

    # Everything the propose job needs, keyed by repository path.
    manifest = {"feature": feature, "stage": stage, "gate": gate, "model": model, "files": []}
    for rel, content in produced.items():
        path = str(feature_path / rel) if rel in ARTIFACT.values() else rel
        target = out_dir / "files" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        manifest["files"].append(path)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    artifact = out_dir / "files" / feature_path / ARTIFACT[stage]
    step_summary(artifact.read_text(encoding="utf-8"))
    set_output(stage=stage, feature=feature, gate=gate)


# ---------------------------------------------------------------- propose

def propose():
    out_dir = Path(env("SDLC_OUT") or fail("SDLC_OUT is not set"))
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    feature, stage, gate = manifest["feature"], manifest["stage"], manifest["gate"]
    features_dir = env("FEATURES_DIR", "sdlc/features").strip("/")
    if stage not in STAGES or "/" in feature or feature.startswith("."):
        fail("The manifest is malformed.")
    feature_path = f"{features_dir}/{feature}"
    files = tracked_files()
    own = f"{feature_path}/{ARTIFACT[stage]}"
    # Doc stages may write only their own artifact. The build may also write what
    # plan.md allows, read from this checkout rather than from the artifact.
    allowed = {own}
    if stage == "build":
        allowed |= set(plan_files(Path(feature_path, "plan.md").read_text(encoding="utf-8")))
    # Check everything before copying anything.
    for path in manifest["files"]:
        why = path_problem(path, files, allowed)
        if why:
            fail(f"Refusing {path}: {why}")
        src = out_dir / "files" / path
        if src.is_symlink() or not src.is_file():
            fail(f"Refusing {path}: not a regular file in the artifact")
    if own not in manifest["files"]:
        fail(f"The artifact has no {own}")
    for path in manifest["files"]:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out_dir / "files" / path, path)

    base = env("BASE_BRANCH") or git("rev-parse", "--abbrev-ref", "HEAD")
    branch = f"sdlc/{feature}/{stage}"
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898283+github-actions[bot]@users.noreply.github.com")
    git("switch", "-C", branch)
    git("add", "--", *manifest["files"])
    title = f"sdlc({feature}): {stage}"
    if stage == "build" and gate != "passed":
        title += " [gate failed]"
    git("commit", "-m", f"{title}\n\nGenerated by the {stage} stage with {manifest['model']}.")
    git("push", "--force", "origin", f"HEAD:refs/heads/{branch}")

    nxt = NEXT_ON_MERGE[stage]
    body = [f"**Stage:** {stage} · **model:** `{manifest['model']}`"
            + (f" · **gate:** {gate}" if stage == "build" else ""), "",
            f"Artifact: [`{own}`]({env('GITHUB_SERVER_URL', 'https://github.com')}/{env('GITHUB_REPOSITORY')}/blob/{branch}/{own})", "",
            "**This PR is the approval gate.** Edit the artifact on this branch if it needs changing, then merge. "
            + (f"Merging starts the **{nxt}** stage." if nxt else "Merging ships the change."), ""]
    if stage == "build" and gate != "passed":
        body.append("The tests did not pass, so this is a draft. The report shows each attempt.")
    body_text = "\n".join(body) + "\n---\n" + Path(own).read_text(encoding="utf-8")[:60000]

    existing = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url", "--jq", ".[0].url")
    if existing:
        sh("gh", "pr", "edit", existing, "--title", title, "--body", body_text)
        url = existing
    else:
        cmd = ["gh", "pr", "create", "--base", base, "--head", branch, "--title", title, "--body", body_text]
        if stage == "build" and gate != "passed":
            cmd.append("--draft")
        url = sh(*cmd)
    print(f"Pull request: {url}")
    step_summary(f"Pull request: {url}")
    set_output(pr=url)


if __name__ == "__main__":
    {"generate": generate, "propose": propose}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: fail(
        "usage: sdlc_stage.py generate|propose"))()
