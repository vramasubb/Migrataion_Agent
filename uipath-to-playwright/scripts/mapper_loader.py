from __future__ import annotations

import argparse
import copy
import json
import os
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPERS_DIR = PROJECT_ROOT / ".claude" / "skills" / "uipath-to-playwright" / "mappers"
if not MAPPERS_DIR.exists():
    MAPPERS_DIR = PROJECT_ROOT / "mappers"


class MapperError(ValueError):
    pass


class MapperLoader:
    def __init__(self, client: str | None = None, mappers_dir: Path = MAPPERS_DIR) -> None:
        self.mappers_dir = mappers_dir
        self.properties = self._read_json("property_mapper.json")
        self.actions = self._read_json("action_mapper.json")
        selected_client = client or os.getenv("UIPATH_PLAYWRIGHT_CLIENT")
        if selected_client:
            self._apply_client(selected_client)
        self._actions_by_tag: dict[str, list[dict[str, Any]]] = {}
        self._anon_counter = 0
        self._index_actions()

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

    def _index_actions(self) -> None:
        for engine, config in self.actions.get("engines", {}).items():
            by_tag: dict[str, list[dict[str, Any]]] = {}
            for action in config.get("actions", []):
                by_tag.setdefault(action["tag"], []).append(action)
            self._actions_by_tag[engine] = by_tag

    def exclude_subtree(self, engine: str) -> set[str]:
        return set(self.actions.get("engines", {}).get(engine, {}).get("excludeSubtree", []))

    def no_op_tags(self, engine: str) -> set[str]:
        return set(self.actions.get("engines", {}).get(engine, {}).get("noOpTags", []))

    def action_for_tag(self, engine: str, tag: str, attrib: dict[str, str]) -> dict[str, Any] | None:
        for action in self._actions_by_tag.get(engine, {}).get(tag, []):
            if self._matches(action.get("match"), attrib):
                return action
        return None

    @staticmethod
    def _matches(condition: dict[str, Any] | None, attrib: dict[str, str]) -> bool:
        if not condition:
            return True
        value = attrib.get(condition["attribute"], "")
        if "in" in condition:
            return value in condition["in"]
        if "endsWith" in condition:
            return value.rstrip().endswith(condition["endsWith"])
        return False

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

    def resolve_ui_locator(self, engine: str, source_class: str, raw_selector: str) -> str:
        """Parse a UiPath selector string and render it as a Playwright locator fragment."""
        parsed = self._parse_selector(raw_selector)
        value, matched_property = self.resolve_or_value(engine, source_class, parsed)
        return self.locator(engine, matched_property, value)

    @staticmethod
    def _parse_selector(raw_selector: str) -> dict[str, str]:
        unescaped = (
            raw_selector.replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&apos;", "'")
            .replace("&amp;", "&")
        )
        parsed = dict(re.findall(r"([\w-]+)\s*=\s*'([^']*)'", unescaped))
        # UiPath wildcard suffix (e.g. name='Continue*') has no Playwright equivalent;
        # strip it and rely on substring text matching instead.
        return {key: value.rstrip("*") for key, value in parsed.items()}

    _STRING_FORMAT_RE = re.compile(r'(?is)^string\.format\(\s*"((?:[^"\\]|\\.)*)"\s*(?:,\s*(.*))?\)$')

    @classmethod
    def _convert_string_format(cls, expression: str) -> str | None:
        """Best-effort VB `String.Format("...{0}...", arg)` -> JS template literal. Returns None if not this shape."""
        match = cls._STRING_FORMAT_RE.match(expression.strip())
        if not match:
            return None
        template, args_text = match.groups()
        args = [part.strip() for part in re.split(r",(?![^(]*\))", args_text)] if args_text else []

        def replace(placeholder: re.Match[str]) -> str:
            index = int(placeholder.group(1))
            return f"${{{args[index]}}}" if index < len(args) else placeholder.group(0)

        substituted = re.sub(r"\{(\d+)\}", replace, template)
        return f"`{substituted}`"

    @classmethod
    def _vb_value(cls, raw_value: str) -> str:
        stripped = (raw_value or "").strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            # A bare VB expression is only valid TS if it's a simple identifier/member access;
            # translate known-risky shapes (e.g. String.Format) instead of emitting invalid syntax.
            converted = cls._convert_string_format(inner)
            return converted if converted is not None else inner
        escaped = stripped.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def render(self, engine: str, action: dict[str, Any], attrib: dict[str, str], selector: str | None) -> str:
        template = action["valueTemplate"]
        token_pattern = re.compile(r"\{([^{}]+)\}")

        def replace(token_match: re.Match[str]) -> str:
            token = token_match.group(1)
            if token == "selector":
                if selector is None:
                    raise MapperError(f"{action['id']}: selector token used without a resolved selector")
                return selector
            if token.startswith("attr:"):
                names = token[len("attr:"):].split(",")
                raw = next((attrib[name] for name in names if attrib.get(name)), "")
                return self._vb_value(raw)
            if token.startswith("bareAttr:"):
                names = token[len("bareAttr:"):].split(",")
                raw = next((attrib[name] for name in names if attrib.get(name)), "").strip()
                if raw.startswith("[") and raw.endswith("]"):
                    raw = raw[1:-1].strip()
                if not raw:
                    # Source activity didn't bind an output variable; synthesize one so the statement stays valid.
                    self._anon_counter += 1
                    raw = f"_result{self._anon_counter}"
                return raw
            if token.startswith("exprVar:"):
                name = token[len("exprVar:"):]
                raw = attrib.get(name, "").strip()
                match = re.match(r"\[(\w+)\]", raw)
                return match.group(1) if match else raw
            if token.startswith("rawAttr:"):
                name = token[len("rawAttr:"):]
                raw = (attrib.get(name) or "").strip()
                if raw.startswith("[") and raw.endswith("]"):
                    raw = raw[1:-1].strip()
                return raw
            if token.startswith("scrollDelta:"):
                name = token[len("scrollDelta:"):]
                direction = (attrib.get(name) or "").strip().lower()
                return "-300" if direction == "up" else "300"
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

    def validate(self) -> list[str]:
        errors: list[str] = []
        for schema_name in ("property_mapper.schema.json", "action_mapper.schema.json"):
            schema_path = self.mappers_dir / "schema" / schema_name
            try:
                with schema_path.open(encoding="utf-8") as stream:
                    json.load(stream)
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"Cannot load schema {schema_name}: {error}")

        if self.properties.get("schemaVersion") != "1.0":
            errors.append("property mapper: schemaVersion must be 1.0")
        if not isinstance(self.properties.get("engines"), dict) or not self.properties["engines"]:
            errors.append("property mapper: engines must be a non-empty object")
        if self.actions.get("schemaVersion") != "2.0":
            errors.append("action mapper: schemaVersion must be 2.0")
        if not isinstance(self.actions.get("engines"), dict) or not self.actions["engines"]:
            errors.append("action mapper: engines must be a non-empty object")

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
                if not action.get("tag"):
                    errors.append(f"{action_id}: missing tag")
        return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and validate UiPath-to-Playwright mappers")
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
