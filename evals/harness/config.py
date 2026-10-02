"""Shared path configuration for the Ritus eval harness."""

from __future__ import annotations

import os
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
EVALS_DIR = HARNESS_DIR.parent
REPO_ROOT = EVALS_DIR.parent
FIXTURE_DIR = EVALS_DIR / "fixture"

ENV_WORKSPACE = "RITUS_EVAL_WORKSPACE"
ENV_SESSION_DIR = "RITUS_EVAL_SESSION_DIR"
ENV_SESSION_STORE = "RITUS_EVAL_SESSION_STORE"
ENV_SESSION_ID = "RITUS_EVAL_SESSION_ID"
ENV_SKILL_CREATOR = "RITUS_EVAL_SKILL_CREATOR"


def path_from_env(name: str, default: Path | None = None) -> Path | None:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser().resolve()
    return default.resolve() if default is not None else None


def text_from_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def default_workspace() -> Path:
    return path_from_env(ENV_WORKSPACE, EVALS_DIR / "workspace")


def default_session_dir() -> Path | None:
    return path_from_env(ENV_SESSION_DIR)


def default_session_store() -> Path:
    return path_from_env(ENV_SESSION_STORE, Path.home() / ".copilot" / "session-store.db")


def default_session_id() -> str:
    return text_from_env(ENV_SESSION_ID)


def default_skill_creator() -> Path | None:
    return path_from_env(ENV_SKILL_CREATOR)


def default_arms() -> dict[str, str]:
    return {"old_skill": "git:fcbd5d5", "new_skill": f"dir:{REPO_ROOT / 'plugin'}"}


def add_common_options(parser, *, arms: bool = False, skill_creator: bool = False):
    parser.add_argument("--workspace", default=None, help=f"Workspace directory (env {ENV_WORKSPACE}; default evals\\workspace)")
    parser.add_argument("--session-dir", default=None, help=f"Copilot session-state directory (env {ENV_SESSION_DIR})")
    parser.add_argument("--session-store", default=None, help=f"Copilot session store DB (env {ENV_SESSION_STORE})")
    parser.add_argument("--session-id", default=None, help=f"Copilot session id (env {ENV_SESSION_ID})")
    if skill_creator:
        parser.add_argument("--skill-creator", default=None, help=f"skill-creator root (env {ENV_SKILL_CREATOR})")
    if arms:
        parser.add_argument("--arm", action="append", default=[], metavar="<name>=<spec>",
                            help=("Arm plugin source; spec is dir:<path> or git:<ref>. May be repeated. "
                                  "Defaults: old_skill=git:fcbd5d5, new_skill=dir:<repo>\\plugin."))


def resolve_workspace(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else default_workspace()


def resolve_session_dir(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else default_session_dir()


def resolve_session_store(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else default_session_store()


def resolve_session_id(value: str | None) -> str:
    return value if value is not None else default_session_id()


def resolve_skill_creator(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else default_skill_creator()
