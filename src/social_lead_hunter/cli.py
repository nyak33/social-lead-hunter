from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from social_lead_hunter.config import load_config, mask_secret
from social_lead_hunter.llm.openai_compatible import OpenAICompatibleClient
from social_lead_hunter.orchestrator import run_cycle
from social_lead_hunter.platforms.threads import ThreadsAdapter
from social_lead_hunter.setup import DEFAULT_CONFIG_PATH, setup_local
from social_lead_hunter.storage.sqlite import SQLiteStorage
from social_lead_hunter.storage.supabase import SupabaseStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="social-lead-hunter", description="Generic social lead discovery and qualification engine")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="create a safe local config and SQLite database")
    setup.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    setup.add_argument("--force", action="store_true", help="replace an existing config with the safe template")

    for name in ("audit", "run", "show-config"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True)
    return parser


def _storage(cfg):
    if cfg.storage_backend == "sqlite":
        return SQLiteStorage(cfg.storage_path)
    if cfg.storage_backend == "supabase":
        return SupabaseStorage()
    raise ValueError(f"unsupported storage backend: {cfg.storage_backend}")


def _print_env_status() -> None:
    for name in ("THREADS_ACCESS_TOKEN", "THREADS_USER_ID", "SUPABASE_URL", "SUPABASE_KEY", "LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL"):
        print(f"{name}: {mask_secret(os.getenv(name))}")


def command_setup(config_path: str, force: bool = False) -> int:
    try:
        result = setup_local(config_path, force=force)
    except Exception as exc:
        print(f"Setup failed: {exc}")
        return 2

    print(f"Config: {result.config_path}")
    print(f"Config status: {'created' if result.created_config else 'kept existing file'}")
    if result.storage_path:
        print(f"SQLite: {result.storage_path}")
    if result.missing_environment:
        print("Missing environment variables: " + ", ".join(result.missing_environment))
    else:
        print("Required runtime environment variables: present")
    print("Safety: dry-run remains enabled unless the local config explicitly changes it")
    return 0


def command_audit(cfg) -> int:
    _print_env_status()
    try:
        adapter = ThreadsAdapter()
    except Exception as exc:
        print(f"Threads: BLOCKED - {exc}")
        return 2
    results = [adapter.validate_identity(), adapter.validate_search_capability(), adapter.validate_reply_capability()]
    for result in results:
        print(f"{result.name}: {'OK' if result.ok else 'BLOCKED'} - {result.detail}")
    return 0 if all(r.ok for r in results) else 2


def command_run(cfg) -> int:
    try:
        adapter = ThreadsAdapter()
        storage = _storage(cfg)
        llm = OpenAICompatibleClient() if cfg.llm_enabled else None
        summary = run_cycle(cfg, adapter, storage, llm=llm)
    except Exception as exc:
        print(f"Run failed: {exc}")
        return 2
    print(f"Mode: {'DRY RUN' if cfg.runtime.dry_run else 'LIVE'}")
    print(json.dumps(asdict(summary), indent=2))
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "setup":
        return command_setup(args.config, force=args.force)

    try:
        cfg = load_config(args.config)
    except Exception as exc:
        print(f"Config error: {exc}")
        return 2

    if args.command == "show-config":
        print(json.dumps(asdict(cfg), indent=2))
        return 0
    if args.command == "audit":
        return command_audit(cfg)
    if args.command == "run":
        return command_run(cfg)
    return 2


if __name__ == "__main__":
    sys.exit(main())
