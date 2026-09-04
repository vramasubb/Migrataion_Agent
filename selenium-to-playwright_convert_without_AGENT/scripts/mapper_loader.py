from __future__ import annotations

import argparse
import copy
import json
import os
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPERS_DIR = PROJECT_ROOT / ".claude" / "skills" / "selenium-to-playwright" / "mappers"
if not MAPPERS_DIR.exists():
    MAPPERS_DIR = PROJECT_ROOT / "mappers"


class MapperError(ValueError):
    pass


class MapperLoader:
    def __init__(self, client: str | None = None, mappers_dir: Path = MAPPERS_DIR) -> None:
        self.mappers_dir = mappers_dir
        self.properties = self._read_json("property_mapper.json")
        self.actions = self._read_json("action_mapper.json")
        selected_client = client or os.getenv("SELENIUM_PLAYWRIGHT_CLIENT")
        if selected_client:
            self._apply_client(selected_client)
        self._compiled_actions: dict[str, list[tuple[dict[str, Any], re.Pattern[str]]]] = {}
        self._compiled_skips: dict[str, list[re.Pattern[str]]] = {}
        self._compile()

    def _read_json(self, relative_path: str) -> dict[str, Any]:
        path = self.mappers_dir / relative_path
        try:
            with path.open(encoding="utf-8") as stream:
                value = json.load(stream)
        except (OSError, json.JSONDecodeError) as error:
            raise MapperError(f"Cannot load {path}: {error}") from error
        if not isinstance(value, dict):
            raise MapperError(f"Mapper root must be an object: {path}")
        return value

    @staticmethod
    def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                MapperLoader._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    def _apply_client(self, client: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", client):
            raise MapperError(f"Invalid client name: {client}")
        overlay = self._read_json(f"clients/{client}.json")
        for engine, object_overrides in overlay.get("propertyOverrides", {}).items():
            object_types = self.properties["engines"][engine]["objectTypes"]
            for object_type, values in object_overrides.items():
                object_types.setdefault(object_type, {})
                self._deep_merge(object_types[object_type], values)

        for engine, changes in overlay.get("actionOverrides", {}).items():
            actions = self.actions["engines"][engine]["actions"]
            remove_ids = set(changes.get("remove", []))
            replacements = {item["id"]: item for item in changes.get("replace", [])}
            actions[:] = [replacements.get(item["id"], item) for item in actions if item["id"] not in remove_ids]
            actions[0:0] = copy.deepcopy(changes.get("add", []))

    def _compile(self) -> None:
        for engine, config in self.actions.get("engines", {}).items():
            self._compiled_actions[engine] = [
                (action, re.compile(action["pattern"])) for action in config.get("actions", [])
            ]
            self._compiled_skips[engine] = [
                re.compile(pattern) for pattern in config.get("skipPatterns", [])
            ]

    def business_type(self, engine: str, source_class: str) -> str:
        return self._object_config(engine, source_class)["targetControlType"]

    def property_priority(self, engine: str, source_class: str) -> list[str]:
        config = self.properties["engines"][engine]
        object_config = config.get("objectTypes", {}).get(source_class, {})
        return list(object_config.get("propertyPriority", config["orLookup"]["defaultPropertyPriority"]))

    def resolve_or_value(
        self, engine: str, source_class: str, raw_props: dict[str, Any]
    ) -> tuple[Any, str]:
        for property_name in self.property_priority(engine, source_class):
            value = raw_props.get(property_name)
            if value not in (None, ""):
                return value, property_name
        raise MapperError(f"No usable locator property for {engine}.{source_class}")

    def match_action(
        self, engine: str, line_or_node: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        del context
        for action, pattern in self._compiled_actions.get(engine, []):
            match = pattern.search(line_or_node)
            if match:
                result = copy.deepcopy(action)
                result["groups"] = list(match.groups())
                result["rendered"] = self.render_template(engine, action["valueTemplate"], match)
                return result
        return None

    def should_skip(self, line_or_node: str, engine: str = "web") -> bool:
        return any(pattern.search(line_or_node) for pattern in self._compiled_skips.get(engine, []))

    def render_template(self, engine: str, template: str, match: re.Match[str]) -> str:
        token_pattern = re.compile(r"\{([^{}]+)\}")

        def replace(token_match: re.Match[str]) -> str:
            token = token_match.group(1)
            if re.fullmatch(r"group\d+", token):
                return self._group(match, token)
            if token.endswith("_x1000") and re.fullmatch(r"group\d+_x1000", token):
                return str(float(self._group(match, token[:-6])) * 1000).removesuffix(".0")
            if token.startswith("first:"):
                return next((self._group(match, name) for name in token.split(":")[1:] if self._group(match, name)), "")
            if token.startswith("locator:"):
                _, strategy_group, value_group = token.split(":", 2)
                return self.locator(engine, self._group(match, strategy_group), self._group(match, value_group))
            raise MapperError(f"Unknown template token: {{{token}}}")

        return token_pattern.sub(replace, template)

    def locator(self, engine: str, strategy: str, value: str) -> str:
        strategies = self.properties["engines"][engine].get("locatorStrategies", {})
        if strategy not in strategies:
            raise MapperError(f"Unknown locator strategy: {engine}.{strategy}")
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return strategies[strategy].replace("{value}", escaped)

    def _object_config(self, engine: str, source_class: str) -> dict[str, Any]:
        try:
            return self.properties["engines"][engine]["objectTypes"][source_class]
        except KeyError as error:
            raise MapperError(f"Unknown object type: {engine}.{source_class}") from error

    @staticmethod
    def _group(match: re.Match[str], token: str) -> str:
        index = int(token.removeprefix("group"))
        return match.group(index) or ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        for schema_name in ("property_mapper.schema.json", "action_mapper.schema.json"):
            schema_path = self.mappers_dir / "schema" / schema_name
            try:
                with schema_path.open(encoding="utf-8") as stream:
                    json.load(stream)
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"Cannot load schema {schema_name}: {error}")

        for mapper_name, mapper in (("property", self.properties), ("action", self.actions)):
            if mapper.get("schemaVersion") != "1.0":
                errors.append(f"{mapper_name} mapper: schemaVersion must be 1.0")
            if not isinstance(mapper.get("engines"), dict) or not mapper["engines"]:
                errors.append(f"{mapper_name} mapper: engines must be a non-empty object")

        seen_ids: set[str] = set()
        property_engines = self.properties.get("engines", {})
        for engine, config in self.actions.get("engines", {}).items():
            if engine not in property_engines:
                errors.append(f"Action engine has no property engine: {engine}")
                continue
            object_types = property_engines[engine].get("objectTypes", {})
            for action in config.get("actions", []):
                action_id = action.get("id", "<missing>")
                if action_id in seen_ids:
                    errors.append(f"Duplicate action id: {action_id}")
                seen_ids.add(action_id)
                if action.get("objectType") not in object_types:
                    errors.append(f"{action_id}: unknown objectType {action.get('objectType')}")
                try:
                    pattern = re.compile(action.get("pattern", ""))
                    sample_groups = pattern.groups
                    for token in re.findall(r"\{group(\d+)(?:_x1000)?\}", action.get("valueTemplate", "")):
                        if int(token) > sample_groups:
                            errors.append(f"{action_id}: template references missing group{token}")
                except re.error as error:
                    errors.append(f"{action_id}: invalid regex: {error}")
            for skip_pattern in config.get("skipPatterns", []):
                try:
                    re.compile(skip_pattern)
                except re.error as error:
                    errors.append(f"{engine}: invalid skip regex {skip_pattern!r}: {error}")
        return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and validate Selenium-to-Playwright mappers")
    parser.add_argument("--client", help="Client overlay name")
    parser.add_argument("--validate", action="store_true", help="Validate all mapper rules")
    args = parser.parse_args()
    loader = MapperLoader(client=args.client)
    if args.validate:
        errors = loader.validate()
        if errors:
            print("Mapper validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Mapper validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())