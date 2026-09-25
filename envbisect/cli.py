"""The ``envbisect`` command-line entry point."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence

from . import __version__
from .diagnose import Diagnoser, DiagnosisProblem
from .report import ConsoleReporter


class _Parser(argparse.ArgumentParser):
    """Use the documented configuration-error exit code for bad CLI input."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"envbisect: error: {message}\n")


def _parser() -> _Parser:
    parser = _Parser(
        prog="envbisect",
        description="Find minimal failure-inducing environment-variable changes.",
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"EnvBisect {__version__}")
    subcommands = parser.add_subparsers(dest="action", required=True, parser_class=_Parser)
    diagnose = subcommands.add_parser(
        "diagnose",
        help="Compare passing and failing dotenv snapshots by running a command",
        description="Run a command under two dotenv snapshots, then minimize the failing changes.",
        epilog="Example: envbisect diagnose --pass working.env --fail broken.env -- pytest",
        allow_abbrev=False,
    )
    diagnose.add_argument("--pass", dest="passing_file", required=True, metavar="FILE")
    diagnose.add_argument("--fail", dest="failing_file", required=True, metavar="FILE")
    diagnose.add_argument(
        "--repeats",
        type=int,
        default=3,
        metavar="N",
        help="runs per baseline and candidate (default: 3)",
    )
    diagnose.add_argument(
        "--timeout",
        type=float,
        metavar="SECONDS",
        help="timeout for each command execution",
    )
    diagnose.add_argument(
        "--quiet", action="store_true", help="print only identified keys on success"
    )
    diagnose.add_argument(
        "--verbose", action="store_true", help="show experiments and redacted output"
    )
    diagnose.add_argument("--no-color", action="store_true", help="disable terminal colors")
    diagnose.add_argument(
        "command", nargs=argparse.REMAINDER, help="command and arguments after --"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return a documented process exit code."""

    parser = _parser()
    args = parser.parse_args(None if argv is None else list(argv))
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        parser.error("a command is required after --")
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("--timeout must be a positive finite number")

    reporter = ConsoleReporter(quiet=args.quiet, verbose=args.verbose, no_color=args.no_color)
    diagnoser = Diagnoser(
        command,
        repeats=args.repeats,
        timeout=args.timeout,
        observer=reporter,
    )
    try:
        result = diagnoser.diagnose(args.passing_file, args.failing_file)
    except DiagnosisProblem as problem:
        reporter.problem(problem, runs=diagnoser.runs)
        return problem.code
    except (OSError, UnicodeError, ValueError) as error:
        # Parser and filesystem errors should not include dotenv contents.
        print(f"EnvBisect configuration error: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("EnvBisect interrupted.", file=sys.stderr)
        return 130
    except Exception as error:
        # Internal exception messages can contain environment values; report
        # the type without dumping potentially sensitive state.
        print(f"EnvBisect internal error ({type(error).__name__}).", file=sys.stderr)
        return 5

    reporter.success(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
