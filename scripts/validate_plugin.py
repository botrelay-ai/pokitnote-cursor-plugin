"""Validate Cursor plugin manifests, MCP config, and skill frontmatter.

The checks are structural. They do not read README.md, so wording edits
there do not fail this script.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

# Field sets follow the Cursor plugin and marketplace schemas published in
# github.com/cursor/plugins (schemas/plugin.schema.json and marketplace.schema.json).
# Marketplace `owner` is required by the Cursor plugins reference.
PLUGIN_KEYS = {
    "name",
    "displayName",
    "description",
    "version",
    "minClientVersions",
    "author",
    "publisher",
    "homepage",
    "repository",
    "license",
    "logo",
    "keywords",
    "category",
    "tags",
    "commands",
    "agents",
    "skills",
    "rules",
    "hooks",
    "variables",
    "mcpServers",
}
MARKETPLACE_KEYS = {"name", "owner", "metadata", "plugins"}
PLUGIN_ENTRY_KEYS = {"name", "source", "description", "minClientVersions"}
KEBAB = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$"
)
SECRET_KEYS = {
    "client_secret",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
}
PRODUCTION_HOST = "pokitnote.com"
PRODUCTION_MCP_URL = "https://pokitnote.com/mcp"
PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def finish(self) -> None:
        if self.errors:
            for message in self.errors:
                print(f"error: {message}", file=sys.stderr)
            raise SystemExit(1)
        print("Plugin manifests, MCP config, and skill frontmatter are valid.")


def load_json(path: Path, report: Report) -> object | None:
    display = path.relative_to(ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(f"{display}: {exc.strerror}")
        return None

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in items:
            if key in parsed:
                report.error(f"{display}: duplicate key {key!r}")
            parsed[key] = value
        return parsed

    try:
        return json.loads(text, object_pairs_hook=pairs)
    except json.JSONDecodeError as exc:
        report.error(f"{display}: {exc.msg} (line {exc.lineno})")
        return None


def require_object(value: object, label: str, report: Report) -> dict[str, object] | None:
    if not isinstance(value, dict):
        report.error(f"{label}: expected a JSON object")
        return None
    return value


def unknown_keys(data: dict[str, object], allowed: set[str], label: str, report: Report) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        report.error(f"{label}: unknown fields {', '.join(extra)}")


def safe_relative(value: object, label: str, report: Report) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        report.error(f"{label}: expected a non-empty path")
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        report.error(f"{label}: path must stay inside the repository ({value})")
        return None
    located = (ROOT / path).resolve()
    root = ROOT.resolve()
    if located != root and root not in located.parents:
        report.error(f"{label}: path must stay inside the repository ({value})")
        return None
    if not located.exists():
        report.error(f"{label}: {value} does not exist")
        return None
    return located


def check_name(value: object, label: str, report: Report, pattern: re.Pattern[str] = KEBAB) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        report.error(f"{label}: expected a lowercase kebab-case name")


def check_https_url(value: object, label: str, report: Report) -> None:
    if not isinstance(value, str):
        report.error(f"{label}: expected a string")
        return
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        report.error(f"{label}: expected an https URL")


def validate_plugin(report: Report) -> dict[str, object] | None:
    path = ROOT / ".cursor-plugin" / "plugin.json"
    data = require_object(load_json(path, report), ".cursor-plugin/plugin.json", report)
    if data is None:
        return None
    unknown_keys(data, PLUGIN_KEYS, ".cursor-plugin/plugin.json", report)
    if "name" not in data:
        report.error(".cursor-plugin/plugin.json: missing required field name")
    else:
        check_name(data["name"], ".cursor-plugin/plugin.json name", report)
    version = data.get("version")
    if version is not None and (not isinstance(version, str) or SEMVER.fullmatch(version) is None):
        report.error(".cursor-plugin/plugin.json version: expected semantic version X.Y.Z")
    author = data.get("author")
    if author is not None:
        author_object = require_object(author, ".cursor-plugin/plugin.json author", report)
        if author_object is not None:
            unknown_keys(author_object, {"name", "email"}, ".cursor-plugin/plugin.json author", report)
            if not isinstance(author_object.get("name"), str) or not author_object["name"].strip():
                report.error(".cursor-plugin/plugin.json author: missing required field name")
    for field in ("homepage", "repository"):
        if field in data:
            check_https_url(data[field], f".cursor-plugin/plugin.json {field}", report)
    if "keywords" in data:
        keywords = data["keywords"]
        if not isinstance(keywords, list) or not all(isinstance(item, str) and item for item in keywords):
            report.error(".cursor-plugin/plugin.json keywords: expected an array of strings")
    for field in ("logo", "skills", "commands", "agents", "rules", "mcpServers"):
        if field not in data:
            continue
        value = data[field]
        values = value if isinstance(value, list) else [value]
        if isinstance(value, list) and not value:
            report.error(f".cursor-plugin/plugin.json {field}: expected at least one path")
        for index, item in enumerate(values):
            label = f".cursor-plugin/plugin.json {field}" if not isinstance(value, list) else (
                f".cursor-plugin/plugin.json {field}[{index}]"
            )
            if not isinstance(item, str):
                report.error(f"{label}: expected a path")
                continue
            if any(char in item for char in "*?["):
                matches = list(ROOT.glob(item))
                if not matches:
                    report.error(f"{label}: {item} matched no files")
                continue
            safe_relative(item, label, report)
    return data


def validate_marketplace(report: Report) -> None:
    path_label = ".cursor-plugin/marketplace.json"
    data = require_object(load_json(ROOT / ".cursor-plugin" / "marketplace.json", report), path_label, report)
    if data is None:
        return
    unknown_keys(data, MARKETPLACE_KEYS, path_label, report)
    for field in ("name", "owner", "plugins"):
        if field not in data:
            report.error(f"{path_label}: missing required field {field}")
    if "name" in data:
        check_name(data["name"], f"{path_label} name", report)
    owner = data.get("owner")
    if owner is not None:
        owner_object = require_object(owner, f"{path_label} owner", report)
        if owner_object is not None:
            unknown_keys(owner_object, {"name", "email"}, f"{path_label} owner", report)
            if not isinstance(owner_object.get("name"), str) or not owner_object["name"].strip():
                report.error(f"{path_label} owner: missing required field name")
    metadata = data.get("metadata")
    if metadata is not None:
        metadata_object = require_object(metadata, f"{path_label} metadata", report)
        description = None if metadata_object is None else metadata_object.get("description")
        if description is not None and not isinstance(description, str):
            report.error(f"{path_label} metadata.description: expected a string")
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return
    if not plugins:
        report.error(f"{path_label}: plugins must list at least one plugin")
        return
    seen: set[str] = set()
    for index, entry in enumerate(plugins):
        label = f"{path_label} plugins[{index}]"
        entry_object = require_object(entry, label, report)
        if entry_object is None:
            continue
        unknown_keys(entry_object, PLUGIN_ENTRY_KEYS, label, report)
        for field in ("name", "source"):
            if field not in entry_object:
                report.error(f"{label}: missing required field {field}")
        name = entry_object.get("name")
        if "name" in entry_object:
            check_name(name, f"{label} name", report)
            if isinstance(name, str):
                if name in seen:
                    report.error(f"{label}: duplicate plugin name {name}")
                seen.add(name)
        source = entry_object.get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        if "://" in source:
            check_https_url(source, f"{label} source", report)
            continue
        located = safe_relative(source, f"{label} source", report)
        if located is None:
            continue
        manifest = located / ".cursor-plugin" / "plugin.json"
        if not manifest.is_file():
            report.error(f"{label}: {source} has no .cursor-plugin/plugin.json")
            continue
        manifest_data = load_json(manifest, report)
        manifest_name = manifest_data.get("name") if isinstance(manifest_data, dict) else None
        if isinstance(name, str) and manifest_name != name:
            display = manifest.relative_to(ROOT).as_posix()
            report.error(f"{label}: name {name!r} does not match {display} name {manifest_name!r}")


def production_url_problem(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != PRODUCTION_HOST:
        return (
            f"server URL must be https://{PRODUCTION_HOST} "
            f"(api.{PRODUCTION_HOST} and stage.{PRODUCTION_HOST} are not the production default)"
        )
    if parsed.port not in {None, 443} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return "server URL must not include a port, user, query, or fragment"
    if parsed.path != "/mcp" or value.endswith("/"):
        return f"server URL must be {PRODUCTION_MCP_URL} with no trailing slash"
    return None


def resolved_mcp_url_problem(value: object, variables: object) -> str | None:
    """Reject a server URL whose published default is not production.

    A literal URL has to be the production MCP URL. A ``${VAR}`` placeholder is
    allowed only when that variable is optional and substituting its default
    produces ``https://pokitnote.com/mcp`` with no trailing slash. Users then
    leave the setting unset. A trailing slash on that default breaks Authenticate.
    """
    if not isinstance(value, str) or not value.strip():
        return "expected a URL"
    names = PLACEHOLDER.findall(value)
    if not names:
        return production_url_problem(value)
    if not isinstance(variables, dict) or variables.get("type") != "object":
        return "plugin variables must declare defaults for the server URL"
    properties = variables.get("properties")
    if not isinstance(properties, dict):
        return "plugin variables.properties must be an object"
    required = variables.get("required", [])
    if not isinstance(required, list):
        return "plugin variables.required must be an array"
    resolved = value
    problems: list[str] = []
    for name in names:
        if name in required:
            problems.append(f"${{{name}}} must be optional so normal use does not need a value")
        prop = properties.get(name)
        if not isinstance(prop, dict):
            problems.append(f"${{{name}}} is not declared in plugin variables")
            continue
        default = prop.get("default")
        if not isinstance(default, str) or not default.strip() or PLACEHOLDER.search(default):
            problems.append(
                f"${{{name}}} needs a literal default of {PRODUCTION_MCP_URL} so users do not have to set it"
            )
            continue
        resolved = resolved.replace("${" + name + "}", default, 1)
    if problems:
        return "; ".join(problems)
    if resolved != PRODUCTION_MCP_URL:
        host_problem = production_url_problem(resolved)
        if host_problem:
            return host_problem
        return f"with defaults applied, the server URL must be {PRODUCTION_MCP_URL}"
    return None


def check_production_url(value: object, label: str, report: Report, variables: object = None) -> None:
    problem = resolved_mcp_url_problem(value, variables)
    if problem:
        report.error(f"{label}: {problem}")


def check_variable_defaults(variables: object, report: Report) -> None:
    if variables is None:
        return
    label = ".cursor-plugin/plugin.json variables"
    if not isinstance(variables, dict):
        report.error(f"{label}: expected a JSON object")
        return
    if variables.get("type") != "object":
        report.error(f"{label}: type must be object")
    properties = variables.get("properties")
    if properties is None:
        return
    if not isinstance(properties, dict):
        report.error(f"{label}.properties: expected a JSON object")
        return
    for name, prop in properties.items():
        prop_label = f"{label}.properties.{name}"
        if not isinstance(prop, dict):
            report.error(f"{prop_label}: expected a JSON object")
            continue
        default = prop.get("default")
        if isinstance(default, str) and "://" in default:
            problem = production_url_problem(default)
            if problem:
                report.error(f"{prop_label} default: {problem}")


def reject_secrets(value: object, label: str, report: Report) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in SECRET_KEYS:
                report.error(f"{label}: {key} does not belong in the plugin config")
            reject_secrets(item, f"{label}.{key}", report)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_secrets(item, f"{label}[{index}]", report)


def validate_mcp(report: Report, variables: object = None) -> None:
    label = "mcp.json"
    data = require_object(load_json(ROOT / "mcp.json", report), label, report)
    if data is None:
        return
    unknown_keys(data, {"mcpServers"}, label, report)
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        report.error(f"{label}: missing required field mcpServers")
        return
    for name, server in servers.items():
        server_label = f"{label} mcpServers.{name}"
        if not isinstance(name, str) or not name.strip():
            report.error(f"{label}: server name must be a non-empty string")
        server_object = require_object(server, server_label, report)
        if server_object is None:
            continue
        if "url" not in server_object:
            report.error(f"{server_label}: missing required field url")
        else:
            check_production_url(server_object["url"], f"{server_label} url", report, variables)
        if server_object.get("type") != "http":
            report.error(f"{server_label}: type must be http")
        for field in ("command", "args"):
            if field in server_object:
                report.error(f"{server_label}: {field} is not used by the remote server")
        auth = server_object.get("auth")
        if not isinstance(auth, dict):
            report.error(f"{server_label}: missing required field auth")
        else:
            client_id = auth.get("CLIENT_ID")
            if not isinstance(client_id, str) or not client_id.strip():
                report.error(f"{server_label} auth: missing required field CLIENT_ID")
            scopes = auth.get("scopes")
            if not isinstance(scopes, list) or not scopes or not all(isinstance(item, str) and item for item in scopes):
                report.error(f"{server_label} auth: missing required field scopes")
        reject_secrets(server_object, server_label, report)


def parse_frontmatter(path: Path, report: Report) -> dict[str, str] | None:
    display = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        report.error(f"{display}: missing frontmatter")
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        report.error(f"{display}: frontmatter is not closed")
        return None
    fields: dict[str, str] = {}
    current: str | None = None
    for line_number, line in enumerate(text[4:end].split("\n"), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] not in " \t":
            if ":" not in line:
                report.error(f"{display}:{line_number}: expected 'key: value'")
                current = None
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip()
            value = raw_value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            if value in {">", "|", ">-", "|-", ">+", "|+"}:
                value = ""
            if key in fields:
                report.error(f"{display}: duplicate frontmatter field {key}")
            fields[key] = value
            current = key
            continue
        if current is None:
            report.error(f"{display}:{line_number}: continuation without a field")
            continue
        extra = line.strip()
        fields[current] = f"{fields[current]} {extra}".strip() if fields[current] else extra
    return fields


def validate_skills(report: Report) -> None:
    skill_files = sorted(path for path in (ROOT / "skills").rglob("SKILL.md") if path.is_file())
    if not skill_files:
        report.error("skills: expected at least one skills/*/SKILL.md")
        return
    for path in skill_files:
        display = path.relative_to(ROOT).as_posix()
        fields = parse_frontmatter(path, report)
        if fields is None:
            continue
        name = fields.get("name", "")
        description = fields.get("description", "")
        if "name" not in fields:
            report.error(f"{display}: missing frontmatter field name")
        elif SKILL_NAME.fullmatch(name) is None:
            report.error(f"{display}: name must be lowercase kebab-case")
        elif name != path.parent.name:
            report.error(f"{display}: name {name!r} must match directory {path.parent.name!r}")
        if "description" not in fields:
            report.error(f"{display}: missing frontmatter field description")
        elif not description.strip():
            report.error(f"{display}: description must not be empty")


def main() -> None:
    report = Report()
    plugin = validate_plugin(report)
    validate_marketplace(report)
    variables = plugin.get("variables") if isinstance(plugin, dict) else None
    check_variable_defaults(variables, report)
    validate_mcp(report, variables)
    validate_skills(report)
    report.finish()


if __name__ == "__main__":
    main()
