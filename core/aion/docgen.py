"""Live argparse CLI Spec Introspector & Reference Doc Generator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def extract_parser_spec(parser: argparse.ArgumentParser) -> Dict[str, Any]:
    """Introspects the live ArgumentParser into a structured command & option schema."""
    global_opts: List[Dict[str, Any]] = []
    subcommands: List[Dict[str, Any]] = []

    subparsers_action = None
    for act in parser._actions:
        if isinstance(act, argparse._SubParsersAction):
            subparsers_action = act
            continue
        if act.dest == "help":
            continue
        global_opts.append(_action_to_dict(act))

    if subparsers_action is not None:
        # Map canonical parser objects cleanly so aliases aren't duplicated as separate blocks
        seen_ids: Dict[int, Dict[str, Any]] = {}
        for name, subp in subparsers_action.choices.items():
            pid = id(subp)
            if pid in seen_ids:
                seen_ids[pid].setdefault("aliases", []).append(name)
                continue
            help_text = ""
            for choice_act in subparsers_action._choices_actions:
                if choice_act.dest == name:
                    help_text = choice_act.help or ""
                    break
            opts = []
            pos = []
            nested_subcommands: List[Dict[str, Any]] = []
            for a in subp._actions:
                if isinstance(a, argparse._SubParsersAction):
                    nested_spec = extract_parser_spec(subp)
                    nested_subcommands = nested_spec.get("subcommands", [])
                    continue
                if a.dest == "help":
                    continue
                d = _action_to_dict(a)
                if a.option_strings:
                    opts.append(d)
                else:
                    pos.append(d)
            entry = {
                "name": name,
                "aliases": [],
                "help": help_text or (subp.description or ""),
                "positionals": pos,
                "options": opts,
                "subcommands": nested_subcommands,
            }
            seen_ids[pid] = entry
            subcommands.append(entry)

    return {
        "prog": Path(parser.prog).name or "pipeline_cli.py",
        "description": parser.description or "",
        "global_options": global_opts,
        "subcommands": subcommands,
    }


def _action_to_dict(act: argparse.Action) -> Dict[str, Any]:
    default = act.default
    if default is argparse.SUPPRESS:
        default = None
    return {
        "flags": list(act.option_strings) if act.option_strings else [act.dest],
        "dest": act.dest,
        "required": bool(getattr(act, "required", False)),
        "choices": list(act.choices) if act.choices else None,
        "default": default,
        "help": act.help or "",
    }


def render_cli_reference_md(spec: Dict[str, Any]) -> str:
    """Renders `CLI_REFERENCE.md` directly from the introspected live parser spec."""
    lines: List[str] = [
        "# AION CLI Command Reference (`CLI_REFERENCE.md`)",
        "",
        "> Auto-generated directly from the live `argparse` tree inside `pipeline_cli.py` via `python pipeline_cli.py cli-spec --write-docs`.",
        "",
        "## Global Invocation",
        "",
        "```bash",
        f"python {spec['prog']} [--project <name>] <subcommand> [options]",
        "```",
        "",
        "### Global Options",
        "",
        "| Flag | Required | Default | Description |",
        "| :--- | :---: | :---: | :--- |",
    ]
    for opt in spec["global_options"]:
        flags = ", ".join(f"`{f}`" for f in opt["flags"])
        lines.append(f"| {flags} | {'Yes' if opt['required'] else 'No'} | `{opt['default']}` | {opt['help']} |")

    lines.extend(["", "## Pipeline Stage Sequence", "", "`script -> voice -> timing -> extract -> semantic-map -> brief -> direct -> motion -> sfx -> render -> qa -> merge`", ""])
    lines.extend(["## Subcommands", ""])

    for sc in spec["subcommands"]:
        aliases = f" (aliases: {', '.join(f'`{a}`' for a in sc['aliases'])})" if sc["aliases"] else ""
        lines.append(f"### `{sc['name']}`{aliases}")
        if sc["help"]:
            lines.append(f"_{sc['help']}_")
        lines.append("")
        pos_str = " ".join(f"<{p['dest']}>" for p in sc["positionals"])
        opt_str = " [options]" if sc["options"] else ""
        lines.append("```bash")
        lines.append(f"python {spec['prog']} {sc['name']}{(' ' + pos_str) if pos_str else ''}{opt_str}")
        lines.append("```")
        if sc["positionals"] or sc["options"]:
            lines.append("")
            lines.append("| Argument / Flag | Required | Choices | Default | Description |")
            lines.append("| :--- | :---: | :--- | :---: | :--- |")
            for item in sc["positionals"] + sc["options"]:
                fl = ", ".join(f"`{f}`" for f in item["flags"])
                req = "Yes" if (item["required"] or item in sc["positionals"]) else "No"
                ch = ", ".join(f"`{c}`" for c in item["choices"]) if item["choices"] else "—"
                dval = f"`{item['default']}`" if item["default"] is not None else "—"
                lines.append(f"| {fl} | {req} | {ch} | {dval} | {item['help']} |")
        for nested in sc.get("subcommands", []):
            lines.append("")
            lines.append(f"#### `{sc['name']} {nested['name']}`")
            if nested.get("help"):
                lines.append(f"_{nested['help']}_")
            lines.append("")
            n_opt = " [options]" if nested.get("options") else ""
            lines.append("```bash")
            lines.append(f"python {spec['prog']} {sc['name']} {nested['name']}{n_opt}")
            lines.append("```")
            if nested.get("positionals") or nested.get("options"):
                lines.append("")
                lines.append("| Argument / Flag | Required | Choices | Default | Description |")
                lines.append("| :--- | :---: | :--- | :---: | :--- |")
                for nitem in nested["positionals"] + nested["options"]:
                    nfl = ", ".join(f"`{f}`" for f in nitem["flags"])
                    nreq = "Yes" if (nitem["required"] or nitem in nested["positionals"]) else "No"
                    nch = ", ".join(f"`{c}`" for c in nitem["choices"]) if nitem["choices"] else "—"
                    ndval = f"`{nitem['default']}`" if nitem["default"] is not None else "—"
                    lines.append(f"| {nfl} | {nreq} | {nch} | {ndval} | {nitem['help']} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
