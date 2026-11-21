# The command line: `python -m tc <command> [options]`.
# This file stays thin: it only parses arguments and hands them to the module that does the work.
# Each command is registered in COMMANDS as: name -> Command(help text, add_args function, run function).
import argparse
from dataclasses import dataclass
from typing import Callable


@dataclass
class Command:
    help: str                                              # one line shown in --help
    add_args: Callable[[argparse.ArgumentParser], None]    # adds this command's own options
    run: Callable[[argparse.Namespace], int]               # does the work, returns an exit code


COMMANDS: dict[str, Command] = {}


def register(name: str, help: str, add_args=lambda p: None):
    """Decorator: @register("doctor", "health check") above a run(args) function adds it to COMMANDS."""
    def wrap(fn):
        COMMANDS[name] = Command(help, add_args, fn)
        return fn
    return wrap


def _not_built(args: argparse.Namespace) -> int:
    print(f"'{args.command}' is not built yet")
    return 1


# Placeholders so --help already shows the plan's commands; real modules replace them as they are built.
for _name, _help in [("doctor", "check tools, keys and disk space"), ("new", "start a new video job"),
                     ("status", "show a job's stages"), ("learn", "save an owner rule")]:
    COMMANDS.setdefault(_name, Command(_help, lambda p: None, _not_built))


def _load_commands() -> None:
    """Import every module that registers commands (each one calls @register when imported)."""
    import importlib
    for mod in ("jobs", "learning", "doctor", "topics", "packaging", "script", "voice", "align", "shots", "run", "finish", "edit", "emblems", "research", "mapcmd", "film", "story", "qa", "viewer", "stillcheck", "motioncheck", "era", "characters", "voices", "caststage", "shotplan", "filmjob"):
        try:
            importlib.import_module(f"tc.{mod}")
        except ModuleNotFoundError as e:
            if e.name != f"tc.{mod}":   # a real missing dependency inside the module: show it
                raise


def main(argv: list[str] | None = None) -> int:
    _load_commands()
    parser = argparse.ArgumentParser(prog="tc", description="Timeless Compass video agent tools")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, cmd in COMMANDS.items():
        p = sub.add_parser(name, help=cmd.help)
        cmd.add_args(p)
    args = parser.parse_args(argv)
    return COMMANDS[args.command].run(args)
