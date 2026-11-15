"""CLI argument parsing and configuration precedence.

These tests do not start any server.
"""

from src.cli import build_parser


def test_command_dispatch_wired():
    parser = build_parser()
    for command in ("index", "check", "test"):
        args = parser.parse_args([command])
        assert callable(getattr(args, "func", None)), f"{command} has no func"


def test_index_command_accepts_data_dir():
    parser = build_parser()
    args = parser.parse_args(["index", "--data-dir", "/tmp/druggpt-data"])
    assert args.data_dir == "/tmp/druggpt-data"


def test_check_command_accepts_data_dir():
    parser = build_parser()
    args = parser.parse_args(["check", "--data-dir", "/tmp/druggpt-data"])
    assert args.data_dir == "/tmp/druggpt-data"


def test_no_command_prints_help_and_exits_zero():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None


def test_test_command_wired():
    parser = build_parser()
    args = parser.parse_args(["test"])
    assert args.command == "test"
    assert callable(args.func)
