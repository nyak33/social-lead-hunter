from social_lead_hunter.cli import build_parser


def test_cli_has_audit_command():
    args = build_parser().parse_args(["audit", "--config", "config.yaml"])
    assert args.command == "audit"
    assert args.config == "config.yaml"


def test_cli_has_run_command():
    args = build_parser().parse_args(["run", "--config", "config.yaml"])
    assert args.command == "run"


def test_cli_has_show_config_command():
    args = build_parser().parse_args(["show-config", "--config", "config.yaml"])
    assert args.command == "show-config"


def test_cli_has_setup_command_with_safe_default_path():
    args = build_parser().parse_args(["setup"])
    assert args.command == "setup"
    assert args.config.endswith(".config/social-lead-hunter/config.yaml")
    assert args.force is False
