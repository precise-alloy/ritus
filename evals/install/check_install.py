#!/usr/bin/env python3
"""Exercise Ritus marketplace installs from the repository layout.

The script builds throwaway marketplace repositories under evals/install/.work,
drives Copilot CLI and Claude Code with throwaway homes, and asserts that the
installed plugin contains only the distributable plugin tree. It also checks
ritus-frontend: a fresh install, sibling discovery by the installed Ritus hook,
and an update from 0.1.0 through the old repository's pointer patch.
"""

from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import shutil
import socketserver
import stat
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_ROOT = Path(__file__).resolve().parent / ".work"
MARKETPLACE_NAME = "precise-alloy-marketplace"
PLUGIN_NAME = "ritus"
CURRENT_VERSION = "3.0.0"
CLONE_STYLE_VERSION = "2.1.2"
DEFAULT_OLD_REFS = ["fcbd5d5", "a610dc5"]
EXPECTED_TOP = [".claude-plugin", "hooks", "scripts", "skills", "templates"]
IGNORED_MARKERS = {".in_use", ".orphaned_at"}
FRONTEND_PLUGIN = "ritus-frontend"
FRONTEND_VERSION = "1.0.0"
FRONTEND_TOP = [".claude-plugin", "ritus-companion.json", "skills"]
FRONTEND_SKILLS = ["frontend", "ui-verify"]
FRONTEND_INTEGRATIONS = 5
# The old repository, precise-alloy/ritus-frontend: origin/main at 0.1.0 and the
# pointer patch that turns its marketplace into a pointer at precise-alloy/ritus.
GITHUB_OWNER = "precise-alloy"
FRONTEND_OLD_MARKETPLACE = "ritus-frontend-marketplace"
FRONTEND_OLD_VERSION = "0.1.0"
DEFAULT_FRONTEND_OLD_REPO = REPO_ROOT.parent / "ritus-frontend"
DEFAULT_FRONTEND_OLD_REF = "dd05c63"
DEFAULT_FRONTEND_POINTER_PATCH = Path(__file__).resolve().parent / "ritus-frontend-pointer.patch"


class CheckError(RuntimeError):
    pass


def rmtree_force(path: Path) -> None:
    def on_error(function, value, _exc_info):  # type: ignore[no-untyped-def]
        try:
            os.chmod(value, stat.S_IWRITE)
            function(value)
        except FileNotFoundError:
            return

    if not path.exists():
        return
    targets = [path]
    if sys.platform == "win32":
        resolved = str(path.resolve())
        if not resolved.startswith("\\\\?\\"):
            targets.append(Path("\\\\?\\" + resolved))
    last_error: OSError | None = None
    for target in targets:
        for _attempt in range(3):
            try:
                shutil.rmtree(target, onerror=on_error)
                return
            except FileNotFoundError:
                return
            except OSError as exc:
                last_error = exc
                time.sleep(1)
    if sys.platform == "win32":
        subprocess.run(
            ["cmd.exe", "/c", "rmdir", "/s", "/q", str(targets[-1])],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not path.exists():
            return
    if last_error:
        raise last_error


def remove_empty_work_root() -> None:
    with contextlib.suppress(OSError):
        WORK_ROOT.rmdir()


@dataclass
class CommandResult:
    args: list[str]
    cwd: Path | None
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


def run(
    args: Iterable[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
) -> CommandResult:
    raw_cmd = [str(a) for a in args]
    cmd = resolve_command(raw_cmd[0]) + raw_cmd[1:]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = CommandResult(cmd, cwd, proc.returncode, proc.stdout, proc.stderr)
    if check and proc.returncode != 0:
        raise CheckError(
            "command failed ({code}): {cmd}\n{out}".format(
                code=proc.returncode,
                cmd=" ".join(cmd),
                out=result.output,
            )
        )
    return result


def run_step(
    step: str,
    args: Iterable[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    access_denied_retries: int = 0,
) -> CommandResult:
    attempts = access_denied_retries + 1
    last: CommandResult | None = None
    for attempt in range(1, attempts + 1):
        result = run(args, cwd=cwd, env=env, input_text=input_text, check=False)
        if result.returncode == 0:
            if attempt > 1:
                print(f"{step}: passed after Access denied retry {attempt - 1}")
            return result
        last = result
        output = result.output
        if "Access is denied. (os error 5)" in output and attempt < attempts:
            print(f"{step}: Access denied on attempt {attempt}; retrying")
            time.sleep(2 * attempt)
            continue
        raise CheckError(
            "step failed: {step}\ncommand failed ({code}): {cmd}\n{out}".format(
                step=step,
                code=result.returncode,
                cmd=" ".join(result.args),
                out=output,
            )
        )
    raise CheckError(f"step failed: {step}\n{last.output if last else ''}")


def resolve_command(executable: str) -> list[str]:
    path = Path(executable)
    if path.is_file():
        if path.suffix.lower() == ".ps1":
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)]
        return [str(path)]
    found = shutil.which(executable)
    if not found and sys.platform == "win32":
        for suffix in (".exe", ".cmd", ".bat", ".ps1"):
            found = shutil.which(executable + suffix)
            if found:
                break
        if not found and executable == "copilot":
            for candidate in (
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "copilot.cmd",
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "copilot.ps1",
            ):
                if candidate.is_file():
                    found = str(candidate)
                    break
    if not found:
        return [executable]
    if found.lower().endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", found]
    return [found]


def copy_tracked_and_untracked(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    result = run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO_ROOT)
    for rel in result.stdout.splitlines():
        if rel.replace("\\", "/").startswith("evals/install/.work/"):
            continue
        src = REPO_ROOT / rel
        if not src.is_file():
            continue
        dst = destination / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def copy_tree_contents(src: Path, dst: Path) -> None:
    if dst.exists():
        rmtree_force(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == ".git":
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def commit_all(repo: Path, message: str) -> None:
    run(["git", "init"], cwd=repo)
    run(["git", "add", "-A"], cwd=repo)
    run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Ritus Install Check",
            "-c",
            "user.email=ritus-install-check@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
    )


def make_current_repo(path: Path) -> Path:
    copy_tracked_and_untracked(path)
    commit_all(path, "current marketplace")
    return path


def make_old_repo(path: Path, old_ref: str, source: Path = REPO_ROOT) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", old_ref],
        cwd=str(source),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if archive.returncode != 0:
        raise CheckError(archive.stderr.decode("utf-8", errors="replace"))
    tar = subprocess.run(
        ["tar", "-xf", "-"],
        cwd=str(path),
        input=archive.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if tar.returncode != 0:
        raise CheckError(tar.stderr.decode("utf-8", errors="replace"))
    commit_all(path, f"old marketplace {old_ref}")
    return path


def old_plugin_manifest(repo: Path) -> Path:
    for candidate in (
        repo / ".claude-plugin" / "plugin.json",
        repo / "plugin" / ".claude-plugin" / "plugin.json",
        repo / "plugins" / PLUGIN_NAME / ".claude-plugin" / "plugin.json",
    ):
        if candidate.is_file():
            return candidate
    raise CheckError(f"could not find {PLUGIN_NAME} plugin manifest in {repo}")


def old_plugin_version(repo: Path) -> str:
    manifest = old_plugin_manifest(repo)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise CheckError(f"{manifest} has no string version")
    return version


def replace_repo_contents(repo: Path, source: Path, message: str) -> None:
    for item in repo.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            rmtree_force(item)
        else:
            item.unlink()
    for item in source.iterdir():
        if item.name == ".git":
            continue
        target = repo / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    run(["git", "add", "-A"], cwd=repo)
    run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Ritus Install Check",
            "-c",
            "user.email=ritus-install-check@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
    )


class GitHttpHandler(http.server.BaseHTTPRequestHandler):
    backend: Path
    project_root: Path
    requests: list[str]

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
        self._serve()

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook name
        self._serve()

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _serve(self) -> None:
        self.requests.append(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0"))
        env = os.environ.copy()
        env.update(
            {
                "GIT_PROJECT_ROOT": str(self.project_root),
                "GIT_HTTP_EXPORT_ALL": "1",
                "REQUEST_METHOD": self.command,
                "PATH_INFO": self.path.split("?", 1)[0],
                "QUERY_STRING": self.path.split("?", 1)[1] if "?" in self.path else "",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(len(body)),
            }
        )
        proc = subprocess.run(
            [str(self.backend)],
            input=body,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        raw = proc.stdout
        sep = b"\r\n\r\n"
        if sep not in raw:
            sep = b"\n\n"
        header_bytes, _, response_body = raw.partition(sep)
        status = 200
        headers: list[tuple[str, str]] = []
        for line in header_bytes.decode("iso-8859-1").splitlines():
            if not line:
                continue
            key, _, value = line.partition(":")
            if key.lower() == "status":
                status = int(value.strip().split()[0])
            elif key and value:
                headers.append((key.strip(), value.strip()))
        if proc.returncode != 0:
            status = 500
            response_body += proc.stderr
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response_body)


@contextlib.contextmanager
def git_http_server(project_root: Path, backend: Path, requests: list[str] | None = None):
    handler = type(
        "RitusGitHttpHandler",
        (GitHttpHandler,),
        {"backend": backend, "project_root": project_root, "requests": requests if requests is not None else []},
    )
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def find_git_http_backend(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    exec_path = run(["git", "--exec-path"], cwd=REPO_ROOT).stdout.strip()
    if exec_path:
        candidates.append(Path(exec_path) / "git-http-backend.exe")
        candidates.append(Path(exec_path) / "git-http-backend")
    candidates.append(Path(r"C:\Program Files\Git\mingw64\libexec\git-core\git-http-backend.exe"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise CheckError("git-http-backend not found; pass --git-http-backend")


def case_env(home: Path) -> dict[str, str]:
    copilot_home = home / "copilot-home"
    copilot_cache = home / "copilot-cache"
    claude_home = home / "claude-home"
    git_config = home / "gitconfig"
    copilot_home.mkdir(parents=True, exist_ok=True)
    copilot_cache.mkdir(parents=True, exist_ok=True)
    claude_home.mkdir(parents=True, exist_ok=True)
    git_config.write_text("[core]\n\tlongpaths = true\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "COPILOT_HOME": str(copilot_home),
            "COPILOT_CACHE_HOME": str(copilot_cache),
            "CLAUDE_CONFIG_DIR": str(claude_home),
            "GIT_CONFIG_GLOBAL": str(git_config),
            "COPILOT_AUTO_UPDATE": "false",
            "NO_COLOR": "1",
        }
    )
    return env


def redirect_github_owner(env: dict[str, str], base_url: str) -> None:
    """Send this case's git traffic for the GitHub owner to the local server."""
    git_config = Path(env["GIT_CONFIG_GLOBAL"])
    lines = [f'[url "{base_url}/{GITHUB_OWNER}/"]']
    for prefix in (
        f"https://github.com/{GITHUB_OWNER}/",
        f"git@github.com:{GITHUB_OWNER}/",
        f"ssh://git@github.com/{GITHUB_OWNER}/",
    ):
        lines.append(f"\tinsteadOf = {prefix}")
    with git_config.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def copilot_install_dir(
    env: dict[str, str], plugin: str = PLUGIN_NAME, marketplace: str = MARKETPLACE_NAME
) -> Path:
    return Path(env["COPILOT_HOME"]) / "installed-plugins" / marketplace / plugin


def claude_install_dir(
    env: dict[str, str],
    version: str = CURRENT_VERSION,
    plugin: str = PLUGIN_NAME,
    marketplace: str = MARKETPLACE_NAME,
) -> Path:
    base = Path(env["CLAUDE_CONFIG_DIR"]) / "plugins" / "cache" / marketplace / plugin
    exact = base / version
    if exact.exists():
        return exact
    versions = sorted([p for p in base.glob("*") if p.is_dir()], key=lambda p: p.stat().st_mtime)
    if versions:
        return versions[-1]
    return exact


def top_entries(path: Path) -> list[str]:
    if not path.exists():
        raise CheckError(f"install directory missing: {path}")
    return sorted(item.name for item in path.iterdir() if item.name not in IGNORED_MARKERS and item.name != ".git")


def assert_top(path: Path) -> list[str]:
    entries = top_entries(path)
    if entries != EXPECTED_TOP:
        raise CheckError(f"{path} has top-level entries {entries}, expected {EXPECTED_TOP}")
    return entries


def copilot_marketplace_add(copilot: str, source: str, env: dict[str, str]) -> None:
    run_step("copilot marketplace add", [copilot, "plugin", "marketplace", "add", source], env=env)


def copilot_marketplace_update(copilot: str, env: dict[str, str]) -> None:
    run_step("copilot marketplace update", [copilot, "plugin", "marketplace", "update"], env=env)


def claude_marketplace_add(claude: str, source: str, env: dict[str, str]) -> None:
    run([claude, "plugin", "marketplace", "add", source], env=env, input_text="y\n")


def claude_marketplace_update(claude: str, env: dict[str, str], marketplace: str = MARKETPLACE_NAME) -> None:
    run([claude, "plugin", "marketplace", "update", marketplace], env=env)


def install_both(
    case_name: str,
    copilot: str,
    claude: str,
    source: str,
    env: dict[str, str],
    plugins: Iterable[str] = (PLUGIN_NAME,),
    marketplace: str = MARKETPLACE_NAME,
) -> None:
    copilot_marketplace_add(copilot, source, env)
    claude_marketplace_add(claude, source, env)
    for plugin in plugins:
        run_step(
            f"{case_name} copilot install {plugin}",
            [copilot, "plugin", "install", f"{plugin}@{marketplace}"],
            env=env,
            access_denied_retries=2,
        )
        run([claude, "plugin", "install", "-y", f"{plugin}@{marketplace}"], env=env, input_text="y\n")


def is_up_to_date_output(output: str) -> bool:
    lower = output.lower()
    return any(
        marker in lower
        for marker in (
            "up to date",
            "up-to-date",
            "already up to date",
            "already up-to-date",
            "already latest",
            "already at latest",
            "nothing to update",
            "no update available",
            "no updates available",
            "no updates found",
        )
    )


def run_plugin_update(
    step: str,
    args: Iterable[str | os.PathLike[str]],
    *,
    env: dict[str, str],
    allow_up_to_date: bool,
    input_text: str | None = None,
    access_denied_retries: int = 0,
) -> CommandResult:
    attempts = access_denied_retries + 1
    last: CommandResult | None = None
    for attempt in range(1, attempts + 1):
        result = run(args, env=env, input_text=input_text, check=False)
        if result.returncode == 0:
            if attempt > 1:
                print(f"{step}: passed after Access denied retry {attempt - 1}")
            return result
        output = result.output
        if allow_up_to_date and is_up_to_date_output(output):
            print(f"{step}: accepted up-to-date outcome")
            return result
        last = result
        if "Access is denied. (os error 5)" in output and attempt < attempts:
            print(f"{step}: Access denied on attempt {attempt}; retrying")
            time.sleep(2 * attempt)
            continue
        raise CheckError(
            "step failed: {step}\ncommand failed ({code}): {cmd}\n{out}".format(
                step=step,
                code=result.returncode,
                cmd=" ".join(result.args),
                out=output,
            )
        )
    raise CheckError(f"step failed: {step}\n{last.output if last else ''}")


def update_copilot(
    case_name: str,
    copilot: str,
    env: dict[str, str],
    *,
    allow_up_to_date: bool,
    plugin: str = PLUGIN_NAME,
    marketplace: str = MARKETPLACE_NAME,
) -> None:
    copilot_marketplace_update(copilot, env)
    run_plugin_update(
        f"{case_name} copilot update",
        [copilot, "plugin", "update", f"{plugin}@{marketplace}"],
        env=env,
        allow_up_to_date=allow_up_to_date,
        access_denied_retries=2,
    )


def update_claude(
    case_name: str,
    claude: str,
    env: dict[str, str],
    *,
    allow_up_to_date: bool,
    plugin: str = PLUGIN_NAME,
    marketplace: str = MARKETPLACE_NAME,
) -> None:
    claude_marketplace_update(claude, env, marketplace)
    run_plugin_update(
        f"{case_name} claude update",
        [claude, "plugin", "update", "-y", f"{plugin}@{marketplace}"],
        env=env,
        input_text="y\n",
        allow_up_to_date=allow_up_to_date,
    )


def update_both(
    case_name: str,
    copilot: str,
    claude: str,
    env: dict[str, str],
    *,
    allow_up_to_date: bool,
) -> None:
    update_copilot(case_name, copilot, env, allow_up_to_date=allow_up_to_date)
    update_claude(case_name, claude, env, allow_up_to_date=allow_up_to_date)


def print_entries(case_name: str, cli: str, entries: list[str]) -> None:
    print(f"{case_name} {cli}: {', '.join(entries)}")


def verify_both(case_name: str, env: dict[str, str]) -> tuple[Path, Path]:
    copilot_dir = copilot_install_dir(env)
    claude_dir = claude_install_dir(env)
    print_entries(case_name, "copilot", assert_top(copilot_dir))
    print_entries(case_name, "claude", assert_top(claude_dir))
    return copilot_dir, claude_dir


def plugin_version(install_dir: Path) -> str:
    manifest = install_dir / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        raise CheckError(f"plugin manifest missing: {manifest}")
    return str(json.loads(manifest.read_text(encoding="utf-8")).get("version"))


def relative_files(root: Path) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and rel.parts[0] != ".git" and path.name not in IGNORED_MARKERS:
            files.add(rel.as_posix())
    return files


def frontend_source_files() -> set[str]:
    prefix = f"plugins/{FRONTEND_PLUGIN}/"
    result = run(["git", "ls-files", "-co", "--exclude-standard", "--", prefix], cwd=REPO_ROOT)
    return {line[len(prefix) :] for line in result.stdout.splitlines() if line.startswith(prefix)}


def frontend_install_dirs(env: dict[str, str], marketplace: str = MARKETPLACE_NAME) -> dict[str, Path]:
    claude_cache = Path(env["CLAUDE_CONFIG_DIR"]) / "plugins" / "cache" / marketplace / FRONTEND_PLUGIN
    return {
        "copilot": copilot_install_dir(env, FRONTEND_PLUGIN, marketplace),
        "claude": claude_cache / FRONTEND_VERSION,
    }


def verify_frontend(case_name: str, cli: str, install_dir: Path, expected_files: set[str]) -> None:
    entries = top_entries(install_dir)
    if entries != FRONTEND_TOP:
        raise CheckError(f"{install_dir} has top-level entries {entries}, expected {FRONTEND_TOP}")
    skills = sorted(item.name for item in (install_dir / "skills").iterdir() if item.is_dir())
    if skills != FRONTEND_SKILLS:
        raise CheckError(f"{install_dir} has skills {skills}, expected {FRONTEND_SKILLS}")
    version = plugin_version(install_dir)
    if version != FRONTEND_VERSION:
        raise CheckError(f"{install_dir} has {FRONTEND_PLUGIN} {version}, expected {FRONTEND_VERSION}")
    installed = relative_files(install_dir)
    if installed != expected_files:
        raise CheckError(
            "{dir} differs from plugins/{plugin}: missing {missing}, unexpected {extra}".format(
                dir=install_dir,
                plugin=FRONTEND_PLUGIN,
                missing=sorted(expected_files - installed),
                extra=sorted(installed - expected_files),
            )
        )
    print(f"{case_name} {cli} {FRONTEND_PLUGIN}: PASS {version}, {', '.join(entries)}; skills {', '.join(skills)}")


def verify_sibling_discovery(
    case_name: str, cli: str, ritus_dir: Path, frontend_dir: Path, case_work: Path, env: dict[str, str]
) -> None:
    project = case_work / "empty-project"
    project.mkdir(parents=True, exist_ok=True)
    hook_env = env.copy()
    for key in ("PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "RITUS_COMPANION_PATHS", "COPILOT_CLI"):
        hook_env.pop(key, None)
    hook_env["CLAUDE_PLUGIN_ROOT"] = str(ritus_dir)
    if cli == "copilot":
        hook_env["COPILOT_CLI"] = "1"
    result = run(
        ["bun", str(ritus_dir / "scripts" / "companion-bootstrap.ts")],
        cwd=project,
        env=hook_env,
        input_text=json.dumps({"cwd": str(project)}),
    )
    if not result.stdout.strip():
        raise CheckError(f"{case_name} {cli}: companion bootstrap found no companions from {ritus_dir}")
    try:
        output = json.loads(result.stdout)
        context = output["additionalContext"] if cli == "copilot" else output["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError) as exc:
        raise CheckError(f"{case_name} {cli}: unexpected companion bootstrap output ({exc})\n{result.output}")
    manifest = os.path.realpath(frontend_dir / "ritus-companion.json")
    expected = f"- {FRONTEND_PLUGIN} ({FRONTEND_INTEGRATIONS} integrations): {manifest}"
    if not any(os.path.normcase(line) == os.path.normcase(expected) for line in context.splitlines()):
        raise CheckError(f"{case_name} {cli}: companion registry lacks '{expected}'\n{context}")
    print(f"{case_name} {cli} sibling discovery: PASS {expected[2:]}")


def verify_fresh_frontend(case_name: str, env: dict[str, str], case_work: Path) -> None:
    expected_files = frontend_source_files()
    ritus_dirs = {"copilot": copilot_install_dir(env), "claude": claude_install_dir(env)}
    for cli, frontend_dir in frontend_install_dirs(env).items():
        verify_frontend(case_name, cli, frontend_dir, expected_files)
        verify_sibling_discovery(case_name, cli, ritus_dirs[cli], frontend_dir, case_work, env)


def verify_runtime_paths(copilot_dir: Path, case_work: Path, env: dict[str, str]) -> None:
    companion_dir = copilot_dir.parent / "ritus-companion"
    companion_dir.mkdir(parents=True, exist_ok=True)
    manifest = companion_dir / "ritus-companion.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "ritus-companion",
                "version": "0.0.0",
                "integrations": [{"skill": "sync", "prompt": "Use the companion during sync."}],
            }
        ),
        encoding="utf-8",
    )
    runtime_env = env.copy()
    runtime_env["PLUGIN_ROOT"] = str(copilot_dir)
    bootstrap = run(
        ["bun", str(copilot_dir / "scripts" / "companion-bootstrap.ts")],
        cwd=case_work,
        env=runtime_env,
    )
    if "ritus-companion.json" not in bootstrap.output:
        raise CheckError("companion bootstrap did not name ritus-companion.json\n" + bootstrap.output)

    empty_project = case_work / "empty-project"
    empty_project.mkdir(parents=True, exist_ok=True)
    sync = run(
        ["bun", str(copilot_dir / "skills" / "sync" / "script" / "sync.ts"), "--check"],
        cwd=empty_project,
        env=env,
        check=False,
    )
    if "could not locate plugin root" in sync.output.lower():
        raise CheckError("sync could not locate plugin root\n" + sync.output)
    if "templates" not in sync.output and "docs/" not in sync.output.replace("\\", "/"):
        raise CheckError("sync --check did not list template files\n" + sync.output)
    print("runtime copilot: companion bootstrap and sync --check passed")


def clone_old_into_install_dirs(old_source: str, old_version: str, env: dict[str, str]) -> None:
    for install_dir in [copilot_install_dir(env), claude_install_dir(env, old_version)]:
        if install_dir.exists():
            rmtree_force(install_dir)
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", old_source, str(install_dir)])


def run_fresh_case(
    name: str,
    source: str,
    copilot: str,
    claude: str,
    run_runtime_assertions: bool,
    work: Path,
) -> None:
    env = case_env(work / "homes")
    install_both(name, copilot, claude, source, env, plugins=(PLUGIN_NAME, FRONTEND_PLUGIN))
    copilot_dir, _ = verify_both(name, env)
    verify_fresh_frontend(name, env, work)
    if run_runtime_assertions:
        verify_runtime_paths(copilot_dir, work, env)


def run_update_case(
    name: str,
    source: str,
    old_clone_source: str,
    mutable_repo: Path,
    current_repo: Path,
    copilot: str,
    claude: str,
    clone_style: bool,
    old_version: str,
    allow_up_to_date: bool,
    work: Path,
) -> None:
    env = case_env(work / "homes")
    install_both(name, copilot, claude, source, env)
    if clone_style:
        clone_old_into_install_dirs(old_clone_source, old_version, env)
    replace_repo_contents(mutable_repo, current_repo, "update marketplace to current")
    update_both(name, copilot, claude, env, allow_up_to_date=allow_up_to_date)
    verify_both(name, env)


def make_github_repos(repos: Path, current_repo: Path, frontend_old_repo: Path, frontend_old_ref: str) -> Path:
    """Serve stand-ins for precise-alloy/ritus (main = the working tree) and
    precise-alloy/ritus-frontend (main = the old 0.1.0 ref); return the latter."""
    try:
        run(["git", "rev-parse", "--verify", f"{frontend_old_ref}^{{commit}}"], cwd=frontend_old_repo)
    except (CheckError, OSError) as exc:
        raise CheckError(
            f"cannot read {frontend_old_ref} from {frontend_old_repo}; pass --frontend-old-repo with a clone "
            f"of {GITHUB_OWNER}/ritus-frontend\n{exc}"
        )
    owner = repos / GITHUB_OWNER
    ritus = owner / "ritus.git"
    run(["git", "clone", "-q", str(current_repo), str(ritus)])
    run(["git", "checkout", "-q", "-B", "main"], cwd=ritus)
    frontend = make_old_repo(owner / "ritus-frontend.git", frontend_old_ref, source=frontend_old_repo)
    run(["git", "checkout", "-q", "-B", "main"], cwd=frontend)
    old_version = plugin_version(frontend)
    if old_version != FRONTEND_OLD_VERSION:
        raise CheckError(f"{frontend_old_ref} has {FRONTEND_PLUGIN} {old_version}, expected {FRONTEND_OLD_VERSION}")
    return frontend


def run_frontend_pointer_case(
    copilot: str,
    claude: str,
    frontend_repo: Path,
    patch: Path,
    base_url: str,
    requests: list[str],
    work: Path,
) -> None:
    name = "frontend-pointer"
    print(f"{name} case: {FRONTEND_PLUGIN} {FRONTEND_OLD_VERSION} from {GITHUB_OWNER}/ritus-frontend, then {patch.name}:")
    env = case_env(work / "homes")
    redirect_github_owner(env, base_url)
    source = f"{base_url}/{GITHUB_OWNER}/{frontend_repo.name}"
    install_both(
        name, copilot, claude, source, env, plugins=(FRONTEND_PLUGIN,), marketplace=FRONTEND_OLD_MARKETPLACE
    )
    old_dirs = {
        "copilot": copilot_install_dir(env, FRONTEND_PLUGIN, FRONTEND_OLD_MARKETPLACE),
        "claude": claude_install_dir(env, FRONTEND_OLD_VERSION, FRONTEND_PLUGIN, FRONTEND_OLD_MARKETPLACE),
    }
    for cli, install_dir in old_dirs.items():
        version = plugin_version(install_dir)
        if version != FRONTEND_OLD_VERSION:
            raise CheckError(f"{name} {cli}: installed {version}, expected {FRONTEND_OLD_VERSION}")
        print(f"{name} {cli}: installed {FRONTEND_PLUGIN} {version}")

    run(["git", "apply", str(patch)], cwd=frontend_repo)
    commit_all(frontend_repo, f"apply {patch.name}")

    expected_files = frontend_source_files()
    ritus_paths = (f"/{GITHUB_OWNER}/ritus.git/", f"/{GITHUB_OWNER}/ritus/")
    for cli in ("copilot", "claude"):
        start = len(requests)
        if cli == "copilot":
            update_copilot(
                name, copilot, env, allow_up_to_date=False, plugin=FRONTEND_PLUGIN, marketplace=FRONTEND_OLD_MARKETPLACE
            )
        else:
            update_claude(
                name, claude, env, allow_up_to_date=False, plugin=FRONTEND_PLUGIN, marketplace=FRONTEND_OLD_MARKETPLACE
            )
        if not any(path.startswith(ritus_paths) for path in requests[start:]):
            raise CheckError(f"{name} {cli}: the update did not fetch {GITHUB_OWNER}/ritus from the local server")
        new_dir = frontend_install_dirs(env, FRONTEND_OLD_MARKETPLACE)[cli]
        verify_frontend(name, cli, new_dir, expected_files)
        print(
            f"{name} {cli} update: PASS {FRONTEND_OLD_VERSION} -> {plugin_version(new_dir)} "
            f"from {GITHUB_OWNER}/ritus plugins/{FRONTEND_PLUGIN} (local server)"
        )


def configure_copilot_github_ref(env: dict[str, str], github: str, github_ref: str) -> None:
    settings = Path(env["COPILOT_HOME"]) / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
    data.setdefault("extraKnownMarketplaces", {})[MARKETPLACE_NAME] = {
        "source": {"source": "github", "repo": github, "ref": github_ref}
    }
    settings.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_github_case(args: argparse.Namespace, old_ref: str) -> None:
    if not args.github:
        return
    print("github update case:")
    work = WORK_ROOT / f"github-{uuid.uuid4().hex}"
    env = case_env(work / "homes")
    old_source = args.github
    copilot_marketplace_add(args.copilot, old_source, env)
    # Claude currently exposes no marketplace-add ref flag. Register main for
    # the old install, then use marketplace update after the user-provided ref
    # has been pushed to the same repository.
    claude_marketplace_add(args.claude, old_source, env)
    run([args.copilot, "plugin", "install", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"], env=env)
    run([args.claude, "plugin", "install", "-y", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"], env=env, input_text="y\n")
    configure_copilot_github_ref(env, args.github, args.github_ref)
    update_both("github-update", args.copilot, args.claude, env, allow_up_to_date=False)
    verify_both("github-update", env)
    if not args.keep:
        rmtree_force(work)
        remove_empty_work_root()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--copilot", default="copilot")
    parser.add_argument("--claude", default="claude")
    parser.add_argument(
        "--old-ref",
        action="append",
        help=(
            "Git ref used as an old install source. Can be supplied more than once; "
            f"default: {', '.join(DEFAULT_OLD_REFS)}"
        ),
    )
    parser.add_argument("--git-http-backend")
    parser.add_argument("--github")
    parser.add_argument("--github-ref")
    parser.add_argument(
        "--frontend-old-repo",
        type=Path,
        default=DEFAULT_FRONTEND_OLD_REPO,
        help=f"Clone of {GITHUB_OWNER}/ritus-frontend, read only; default: {DEFAULT_FRONTEND_OLD_REPO}",
    )
    parser.add_argument(
        "--frontend-old-ref",
        default=DEFAULT_FRONTEND_OLD_REF,
        help=f"{FRONTEND_PLUGIN} {FRONTEND_OLD_VERSION} commit in that clone; default: {DEFAULT_FRONTEND_OLD_REF}",
    )
    parser.add_argument(
        "--frontend-pointer-patch",
        type=Path,
        default=DEFAULT_FRONTEND_POINTER_PATCH,
        help=f"Pointer patch for the old repository; default: {DEFAULT_FRONTEND_POINTER_PATCH.name}",
    )
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    args.old_ref = args.old_ref or DEFAULT_OLD_REFS
    if args.github and not args.github_ref:
        parser.error("--github-ref is required with --github")
    if not args.frontend_pointer_patch.is_file():
        parser.error(f"--frontend-pointer-patch not found: {args.frontend_pointer_patch}")
    return args


def safe_ref_name(ref: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ".-" else "-" for ch in ref)


def main() -> int:
    args = parse_args()
    run([args.copilot, "--version"])
    run([args.claude, "--version"])
    run(["bun", "--version"])
    backend = find_git_http_backend(args.git_http_backend)

    run_id = uuid.uuid4().hex
    work = WORK_ROOT / run_id
    repos = work / "repos"
    current_repo = make_current_repo(repos / "current")
    old_repos = {
        old_ref: make_old_repo(repos / f"old-{safe_ref_name(old_ref)}", old_ref)
        for old_ref in args.old_ref
    }
    requests: list[str] = []

    try:
        frontend_old_repo = make_github_repos(repos, current_repo, args.frontend_old_repo, args.frontend_old_ref)
        run_fresh_case("fresh-local", str(current_repo), args.copilot, args.claude, True, work / "fresh-local")

        with git_http_server(repos, backend, requests) as base_url:
            run_fresh_case(
                "fresh-git",
                f"{base_url}/current/.git",
                args.copilot,
                args.claude,
                False,
                work / "fresh-git",
            )
            run_frontend_pointer_case(
                args.copilot,
                args.claude,
                frontend_old_repo,
                args.frontend_pointer_patch.resolve(),
                base_url,
                requests,
                work / "fe-ptr",
            )

            for old_ref, old_repo in old_repos.items():
                ref_name = safe_ref_name(old_ref)
                old_version = old_plugin_version(old_repo)
                allow_up_to_date = old_version == CURRENT_VERSION
                print(f"update cases for {old_ref} ({old_version}):")

                local_mutable = repos / f"local-mutable-{ref_name}"
                copy_tree_contents(old_repo, local_mutable)
                commit_all(local_mutable, f"old mutable marketplace {old_ref}")
                run_update_case(
                    f"update-{ref_name}-local",
                    str(local_mutable),
                    str(old_repo),
                    local_mutable,
                    current_repo,
                    args.copilot,
                    args.claude,
                    False,
                    old_version,
                    allow_up_to_date,
                    work / f"update-{ref_name}-local",
                )

                git_mutable = repos / f"git-mutable-{ref_name}"
                copy_tree_contents(old_repo, git_mutable)
                commit_all(git_mutable, f"old git mutable marketplace {old_ref}")
                run_update_case(
                    f"update-{ref_name}-git",
                    f"{base_url}/{git_mutable.name}/.git",
                    f"{base_url}/{old_repo.name}/.git",
                    git_mutable,
                    current_repo,
                    args.copilot,
                    args.claude,
                    False,
                    old_version,
                    allow_up_to_date,
                    work / f"update-{ref_name}-git",
                )

                if old_version == CLONE_STYLE_VERSION:
                    local_clone_mutable = repos / f"local-clone-mutable-{ref_name}"
                    copy_tree_contents(old_repo, local_clone_mutable)
                    commit_all(local_clone_mutable, f"old local clone mutable marketplace {old_ref}")
                    run_update_case(
                        f"clone-update-{ref_name}-local",
                        str(local_clone_mutable),
                        str(old_repo),
                        local_clone_mutable,
                        current_repo,
                        args.copilot,
                        args.claude,
                        True,
                        old_version,
                        allow_up_to_date,
                        work / f"clone-update-{ref_name}-local",
                    )

                    git_clone_mutable = repos / f"git-clone-mutable-{ref_name}"
                    copy_tree_contents(old_repo, git_clone_mutable)
                    commit_all(git_clone_mutable, f"old git clone mutable marketplace {old_ref}")
                    run_update_case(
                        f"clone-update-{ref_name}-git",
                        f"{base_url}/{git_clone_mutable.name}/.git",
                        f"{base_url}/{old_repo.name}/.git",
                        git_clone_mutable,
                        current_repo,
                        args.copilot,
                        args.claude,
                        True,
                        old_version,
                        allow_up_to_date,
                        work / f"clone-update-{ref_name}-git",
                    )

        run_github_case(args, args.old_ref[0])
        print("all install checks passed")
        return 0
    finally:
        if args.keep:
            print(f"kept work directory: {work}")
        else:
            rmtree_force(work)
            remove_empty_work_root()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
