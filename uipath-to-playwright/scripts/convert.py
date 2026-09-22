from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mapper_loader import MapperError, MapperLoader
from token_usage import build_token_report, print_token_summary


@dataclass
class ConversionResult:
    source: str
    output: str
    mapped_actions: int
    skipped_lines: int
    unmatched_lines: int
    action_ids: list[str] = field(default_factory=list)
    action_records: list[dict] = field(default_factory=list)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


_ACTION_LINE_RE = re.compile(r"\.(click|fill|check|uncheck|selectOption)\(")


def _slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower() or "test"


def _inject_screenshots(lines: list[str], screenshots_dir: str, test_slug: str) -> list[str]:
    """Insert a page.screenshot() call after every UI action line, numbered in execution order."""
    result: list[str] = []
    counter = 0
    for line in lines:
        result.append(line)
        match = _ACTION_LINE_RE.search(line)
        if match:
            counter += 1
            indent = line[: len(line) - len(line.lstrip())]
            path = f"{screenshots_dir}/{test_slug}/{counter:02d}-{match.group(1)}.png"
            result.append(f"{indent}await page.screenshot({{ path: '{path}' }});")
    return result


def _find_child_by_suffix(element: ET.Element, suffix: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag).endswith(suffix):
            return child
    return None


def _find_descendant_by_local_name(element: ET.Element, name: str) -> ET.Element | None:
    for descendant in element.iter():
        if _local_name(descendant.tag) == name:
            return descendant
    return None


def _strip_brackets(raw: str | None) -> str:
    text = (raw or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1].strip()
    return text


_JS_LITERAL_RE = re.compile(r"^(-?\d+(\.\d+)?|true|false|null)$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")

# Known VB/.NET API shapes with a direct, safe TS translation (no invented business logic — these are
# structural/administrative calls: path joining, regex extraction, and the project's own global config).
_GLOBAL_VAR_RE = re.compile(r"GlobalVariablesNamespace\.GlobalVariables\.(\w+)")
_DT_ROWS_CELL_RE = re.compile(r"(\w+)\.Rows\((\d+)\)\(\"(\w+)\"\)")
_DT_ITEM_RE = re.compile(r"(\w+)\.Item\(\"(\w+)\"\)")
_TOSTRING_RE = re.compile(r"^(\S+)\.ToString\(\)$")
# Embedded (not whole-string) `.ToString()` calls, e.g. inside a larger concatenation expression like
# `(Header_idx + 1).ToString() + "." + counter.ToString()` — common in screenshot filename expressions.
_PAREN_TOSTRING_RE = re.compile(r"(?<![\w)])\(([^()]*)\)\.ToString\(\)")
_BARE_TOSTRING_RE = re.compile(r"\b([A-Za-z_]\w*)\.ToString\(\)")
_PATH_COMBINE_RE = re.compile(r"^System\.IO\.Path\.Combine\((.+)\)$")
_REGEX_MATCH_RE = re.compile(r'^System\.Text\.RegularExpressions\.Regex\.Match\((.+?),\s*"((?:[^"\\]|\\.)*)"\)\.Value$')
# `New SystemException("...")` / `New Exception("...")` (Throw activity) -> a real JS Error.
_NEW_EXCEPTION_RE = re.compile(r'^New\s+\w*Exception\("((?:[^"\\]|\\.)*)"\)$')
# `String.IsNullOrEmpty(x)` / `Not String.IsNullOrEmpty(x)` -> plain JS falsy/truthy checks.
_NOT_ISNULLOREMPTY_RE = re.compile(r"^Not\s+String\.IsNullOrEmpty\((.+)\)$")
_ISNULLOREMPTY_RE = re.compile(r"^String\.IsNullOrEmpty\((.+)\)$")
# `Timespan.Parse("HH:MM:SS")` (Delay activity, static) and `Timespan.Parse(<dynamic expr>)`.
_TIMESPAN_LITERAL_RE = re.compile(r'^Timespan\.Parse\("(\d+):(\d+):(\d+(?:\.\d+)?)"\)$')
_TIMESPAN_DYNAMIC_RE = re.compile(r"^Timespan\.Parse\((.+)\)$")
# Plain double-quoted string literals left over after the specific translations above have already
# consumed their own quoted segments (Path.Combine args, Regex patterns, exception messages, ...).
_PLAIN_STRING_LITERAL_RE = re.compile(r'"([^"]*)"')
# A bare URL (scheme://...) or Windows drive-letter path (C:\... or C:/...) literal — quoted as a raw
# string even though it contains dots (which would otherwise look like VB member-access).
_URL_OR_PATH_LITERAL_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.\-]*://|[A-Za-z]:[\\/])")
# VB syntax with no valid JS equivalent at all (would hard-fail `tsc`, not just need review): inline
# `If(cond, a, b)` ternary calls, `Nothing`, `AndAlso`/`OrElse`/bare `Or`/`And` boolean operators, and the
# `&` string-concatenation operator.
# VB syntax with no valid JS equivalent at all (would hard-fail `tsc`, not just need review): inline
# `If(cond, a, b)` ternary calls, `Nothing`, `AndAlso`/`OrElse`/bare `Or`/`And`/`Not` boolean operators, and
# the `&` string-concatenation operator.
_INVALID_JS_SYNTAX_RE = re.compile(r"\bIf\(|\bNothing\b|\bAndAlso\b|\bOrElse\b|\bOr\b|\bAnd\b|\bNot\b|\"\s*&\s*|\s*&\s*\"")


def _to_lower_camel(name: str) -> str:
    return name[:1].lower() + name[1:] if name else name


def _translate_known_dotnet_calls(text: str) -> str:
    """Best-effort translation of recurring VB/.NET API shapes into valid TypeScript."""
    not_isempty_match = _NOT_ISNULLOREMPTY_RE.match(text)
    if not_isempty_match:
        text = f"!!({not_isempty_match.group(1)})"
    else:
        isempty_match = _ISNULLOREMPTY_RE.match(text)
        if isempty_match:
            text = f"!({isempty_match.group(1)})"
    text = _GLOBAL_VAR_RE.sub(lambda m: f"env.{_to_lower_camel(m.group(1))}", text)
    text = _DT_ROWS_CELL_RE.sub(lambda m: f"{m.group(1)}[{m.group(2)}]['{m.group(3)}']", text)
    text = _DT_ITEM_RE.sub(lambda m: f"{m.group(1)}['{m.group(2)}']", text)
    text = _PAREN_TOSTRING_RE.sub(lambda m: f"String({m.group(1)})", text)
    text = _BARE_TOSTRING_RE.sub(lambda m: f"String({m.group(1)})", text)

    combine_match = _PATH_COMBINE_RE.match(text)
    if combine_match:
        parts = combine_match.group(1).split(",", 1)
        if len(parts) == 2:
            text = f"`${{{parts[0].strip()}}}/${{{parts[1].strip()}}}`"

    regex_match = _REGEX_MATCH_RE.match(text)
    if regex_match:
        text = f"({regex_match.group(1).strip()}.match(/{regex_match.group(2)}/) ?? [''])[0]"

    new_exception_match = _NEW_EXCEPTION_RE.match(text)
    if new_exception_match:
        text = f'new Error("{new_exception_match.group(1)}")'

    tostring_match = _TOSTRING_RE.match(text)
    if tostring_match:
        text = f"String({tostring_match.group(1)})"

    # VB string literals don't use backslash-escaping (a literal `\` is just a character) — but once
    # passed straight through into a JS/TS double-quoted string it must be escaped, or JS misreads e.g.
    # `\6` as an (invalid, disallowed) octal escape, or a trailing `\"` as an escaped quote that swallows
    # the rest of the line. Applied last so it never touches quoted segments already consumed above
    # (Path.Combine args, Regex patterns, exception messages).
    text = _PLAIN_STRING_LITERAL_RE.sub(lambda m: '"' + m.group(1).replace("\\", "\\\\") + '"', text)
    return text


def _convert_vb_expression(raw: str | None) -> tuple[str, bool]:
    text = _strip_brackets(raw)
    if not text:
        return "''", False
    translated = _translate_known_dotnet_calls(text)
    if translated != text:
        return translated, False
    # A bare (non-bracket-bound) value that isn't a quoted/numeric/boolean literal, identifier, or member/
    # index expression is a raw source string (e.g. an unquoted folder path) — quote it so it's valid TS.
    # A URL/Windows-path literal (e.g. `file:///C:/...`) also needs quoting even though it contains dots —
    # those aren't VB member-access, they're part of the path/domain/extension text.
    if (_URL_OR_PATH_LITERAL_RE.match(text)) or (
        not text.startswith(('"', "'"))
        and "(" not in text
        and "." not in text
        and "[" not in text
        and not _JS_LITERAL_RE.match(text)
        and not _IDENTIFIER_RE.match(text)
    ):
        escaped = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'", False
    # Some VB expression shapes (inline `If(cond, a, b)` ternary calls, `Nothing`, `AndAlso`/`OrElse`/bare
    # `Or`/`And` boolean operators, `&` string concatenation) are NOT valid JS syntax at all — passing them
    # through as-is would hard-fail `tsc`, not just need review. Substitute a safe placeholder instead and
    # keep the original VB source visible in a comment, so the file still compiles and a human can finish it.
    if _INVALID_JS_SYNTAX_RE.search(text):
        preserved = text.replace("*/", "* /")
        return f"(undefined as any) /* VERIFY (unsupported VB syntax): {preserved} */", True
    # Any remaining call-shaped expression is a VB/.NET API with no recognized TS equivalent — pass it
    # through but flag it for human review rather than guessing a translation.
    flagged = "(" in text or any(token in text for token in ("vbCrLf", "Nothing", "AndAlso", "OrElse"))
    return text, flagged


_X_NAMESPACE = "{http://schemas.microsoft.com/winfx/2006/xaml}"


def _x_key(element: ET.Element) -> str | None:
    return element.attrib.get(f"{_X_NAMESPACE}Key") or element.attrib.get("Key")


def normalize_workflow_path(raw: str) -> str:
    """Normalize a UiPath WorkflowFileName so it can be used as a component-registry key."""
    return raw.replace("\\", "/").strip().lower()


def _camel_case(kebab: str) -> str:
    parts = kebab.split("-")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


class ProjectWalker:
    """Walks a parsed UiPath Activity XML tree and emits Playwright TypeScript statements."""

    def __init__(
        self,
        loader: MapperLoader,
        engine: str = "web",
        component_registry: dict[str, dict] | None = None,
        fixture_slug: str | None = None,
        source_text: str | None = None,
    ) -> None:
        self.loader = loader
        self.engine = engine
        self.exclude_subtree = loader.exclude_subtree(engine)
        self.no_op_tags = loader.no_op_tags(engine)
        self.mapped_ids: list[str] = []
        self.mapped_records: list[dict] = []  # {tag, selector, rendered} — real per-occurrence evidence
        self.unmatched: list[str] = []
        self.structural_count = 0
        self.test_name: str | None = None
        self.component_registry = component_registry
        self.used_components: dict[str, dict] = {}
        # When set (project_convert.py only), ReadRange wires a real fixture import instead of a bare TODO.
        self.fixture_slug = fixture_slug
        self.source_text = source_text or ""
        self.fixture_imports: dict[str, str] = {}  # dt_var -> import path
        self.fixture_columns: dict[str, set[str]] = {}  # dt_var -> referenced column names
        self.declared_vars: set[str] = set()

    def walk_root(self, root: ET.Element) -> list[str]:
        lines: list[str] = []
        self.walk(root, lines, indent="  ")
        return lines

    def walk(self, element: ET.Element, out: list[str], indent: str) -> None:
        tag = _local_name(element.tag)

        if tag in self.exclude_subtree:
            self.structural_count += 1
            return
        if tag in self.no_op_tags:
            self.structural_count += 1
            return

        if tag == "InvokeWorkflowFile" and self.component_registry is not None:
            self._handle_invoke_workflow_file(element, out, indent)
            return
        if tag == "ReadRange" and self.fixture_slug is not None:
            self._handle_read_range(element, out, indent)
            return

        action = self.loader.action_for_tag(self.engine, tag, element.attrib)
        if action is not None:
            try:
                selector = self._resolve_selector(action, element)
                rendered = self.loader.render(self.engine, action, element.attrib, selector)
            except MapperError as error:
                # Never let one unresolvable selector/expression (e.g. a UiPath descriptor property this
                # mapper doesn't yet recognize) crash the whole file — flag it honestly and keep going, so
                # any UiPath project can still be converted end to end.
                display_name = element.attrib.get("DisplayName", "")
                out.append(f"{indent}// TODO: unmapped activity <{tag}> {display_name} ({error})".rstrip())
                self.unmatched.append(f"{tag} ({display_name}): {error}")
                return
            rendered = self._dedupe_declarations(rendered)
            out.append(f"{indent}{rendered}")
            self.mapped_ids.append(action["id"])
            self.mapped_records.append({"tag": tag, "selector": selector, "rendered": rendered})
            return

        if tag == "StartTest":
            self.test_name = element.attrib.get("TestName") or self.test_name
            self.structural_count += 1
            return
        if tag == "GetRobotAsset":
            self._handle_get_robot_asset(element, out, indent)
            return
        if tag == "MultipleAssign":
            self._handle_multiple_assign(element, out, indent)
            return
        if tag == "Assign":
            self._handle_assign(element, out, indent)
            return
        if tag == "ForEachRow":
            self._handle_for_each_row(element, out, indent)
            return
        if tag == "NCheckState":
            self._handle_ncheckstate(element, out, indent)
            return
        if tag == "Sequence.Variables":
            self._handle_sequence_variables(element, out, indent)
            return
        if tag == "If":
            self._handle_if(element, out, indent)
            return
        if tag == "TryCatch":
            self._handle_trycatch(element, out, indent)
            return
        if tag == "ForEach":
            self._handle_foreach(element, out, indent)
            return
        if tag == "NApplicationCard":
            self._handle_napplicationcard(element, out, indent)
            return
        if tag == "NTakeScreenshot":
            self._handle_take_screenshot(element, out, indent)
            return
        if tag == "Throw":
            self._handle_throw(element, out, indent)
            return
        if tag == "GetLastDownloadedFile":
            self._handle_get_last_downloaded_file(element, out, indent)
            return
        if tag == "Delay":
            self._handle_delay(element, out, indent)
            return

        children = list(element)
        if not children:
            display_name = element.attrib.get("DisplayName", "")
            if display_name or element.attrib:
                self.unmatched.append(f"{tag} ({display_name})" if display_name else tag)
                out.append(f"{indent}// TODO: unmapped activity <{tag}> {display_name}".rstrip())
            else:
                self.structural_count += 1
            return

        self.structural_count += 1
        for child in children:
            self.walk(child, out, indent)

    def _handle_sequence_variables(self, element: ET.Element, out: list[str], indent: str) -> None:
        """Pre-declared workflow variables (`Sequence.Variables`) need a real `let` at their declaration
        point, or references to them after a nested block (e.g. after a ForEachRow loop) fall out of scope."""
        start = len(out)
        for var in element:
            if _local_name(var.tag) != "Variable":
                continue
            name = var.attrib.get("Name")
            if not name:
                continue
            type_attr = var.attrib.get(f"{_X_NAMESPACE}TypeArguments", "")
            default = var.attrib.get("Default")
            type_annotation = ""
            if default is None:
                js_value = "''" if "String" in type_attr else "undefined"
                # No default value AND not a string default's safe `''` fallback — annotate `: any` so this
                # variable's type isn't permanently inferred as the literal type `undefined` (which would
                # make every later assignment/use of it a strict-mode compile error).
                if js_value == "undefined":
                    type_annotation = ": any"
            elif "Boolean" in type_attr:
                js_value = default.lower()
            elif "Int32" in type_attr or "Double" in type_attr:
                js_value = default
            else:
                js_value = f"'{default.replace(chr(92), chr(92) * 2).replace(chr(39), chr(92) + chr(39))}'"
            self.declared_vars.add(name)
            out.append(f"{indent}let {name}{type_annotation} = {js_value};")
        self.mapped_ids.append("sequence.variables")
        self.mapped_records.append({"tag": "Sequence.Variables", "selector": None, "rendered": "\n".join(line.strip() for line in out[start:])})

    def _handle_invoke_workflow_file(self, element: ET.Element, out: list[str], indent: str) -> None:
        workflow_file = element.attrib.get("WorkflowFileName", "")
        component = self.component_registry.get(normalize_workflow_path(workflow_file)) if self.component_registry else None
        if component is None:
            out.append(f"{indent}// TODO: inline reusable component '{workflow_file}' as a Playwright page-object method")
            self.unmatched.append(f"InvokeWorkflowFile ({workflow_file})")
            return

        call_args: dict[str, str] = {}
        args_container = _find_child_by_suffix(element, ".Arguments")
        if args_container is not None:
            for arg in args_container:
                if _local_name(arg.tag) != "InArgument":
                    continue
                key = _x_key(arg)
                if key:
                    call_args[key] = (arg.text or "").strip()

        params = component["params"]
        if params:
            # Call-site arguments are plain string literals (not UiPath [var] bindings), so quote them directly.
            entries = ", ".join(
                f"{name}: '{call_args.get(name, '').replace(chr(39), chr(92) + chr(39))}'" for name, _ in params
            )
            args_str = f"{{ {entries} }}"
        else:
            args_str = ""
        out.append(f"{indent}await {component['instance_var']}.{component['method_name']}({args_str});")
        self.mapped_ids.append("invoke.page.object")
        self.mapped_records.append({"tag": "InvokeWorkflowFile", "selector": None, "rendered": out[-1].strip()})
        self.used_components[normalize_workflow_path(workflow_file)] = component

    def _emit_assignment(self, var_name: str, js_value: str, flagged: bool, out: list[str], indent: str) -> None:
        is_simple_identifier = bool(_IDENTIFIER_RE.match(var_name))
        # A translated indexer/member target (e.g. `dt[0]['Col']`) is valid TS on its own; only flag when
        # it still contains an unresolved call (`(`), meaning a genuinely-unknown API slipped through.
        still_risky = flagged or "(" in var_name
        suffix = "  // VERIFY: VB expression" if still_risky else ""
        if is_simple_identifier and var_name not in self.declared_vars:
            self.declared_vars.add(var_name)
            out.append(f"{indent}let {var_name} = {js_value};{suffix}")
        else:
            out.append(f"{indent}{var_name} = {js_value};{suffix}")

    def _resolve_selector(self, action: dict, element: ET.Element) -> str | None:
        spec = action.get("selector")
        if not spec:
            return None
        object_type = action["objectType"]
        if spec["mode"] == "attribute":
            raw = next((element.attrib[name] for name in spec["attributes"] if element.attrib.get(name)), None)
            if raw is None:
                raise MapperError(f"{action['id']}: no selector attribute present on <{_local_name(element.tag)}>")
            return self.loader.resolve_ui_locator(self.engine, object_type, raw)
        if spec["mode"] == "target":
            target = _find_child_by_suffix(element, ".Target")
            anchor = None
            if target is not None:
                for name in spec["anchorLocalNames"]:
                    anchor = _find_descendant_by_local_name(target, name)
                    if anchor is not None:
                        break
            if anchor is None:
                raise MapperError(f"{action['id']}: no <...Target> descriptor found on <{_local_name(element.tag)}>")
            raw = next((anchor.attrib[name] for name in spec["attributes"] if anchor.attrib.get(name)), None)
            if raw is None:
                raise MapperError(f"{action['id']}: target descriptor has no usable selector attribute")
            return self.loader.resolve_ui_locator(self.engine, object_type, raw)
        raise MapperError(f"{action['id']}: unknown selector mode {spec['mode']}")

    def _dedupe_declarations(self, rendered: str) -> str:
        """Demote `let`/`const X = ...` to a plain assignment when X was already declared elsewhere
        (e.g. pre-declared in Sequence.Variables), so the same name is never redeclared in one scope."""

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name in self.declared_vars:
                return f"{name} = "
            self.declared_vars.add(name)
            return match.group(0)

        return re.sub(r"\b(?:let|const)\s+(\w+)\s*(?::[^=]+)?=\s*", replace, rendered)

    def _handle_read_range(self, element: ET.Element, out: list[str], indent: str) -> None:
        dt_var = _strip_brackets(element.attrib.get("DataTable"))
        if not _IDENTIFIER_RE.match(dt_var or ""):
            # No variable actually captures this read's result (e.g. DataTable="{x:Null}") — nothing to wire.
            sheet = _strip_brackets(element.attrib.get("SheetName")) or ""
            out.append(f"{indent}// TODO: load test data from '{element.attrib.get('WorkbookPath', '')}' sheet {sheet} into a TypeScript fixture")
            self.mapped_ids.append("read.range")
            self.mapped_records.append({"tag": "ReadRange", "selector": None, "rendered": out[-1].strip()})
            return
        data_ident = f"{_camel_case(self.fixture_slug)}Data"
        import_path = f"../../test-data/{self.fixture_slug}-data.json"
        self.fixture_imports[dt_var] = f"import {data_ident} from '{import_path}';"
        columns = set()
        for match in re.finditer(rf"{re.escape(dt_var)}\.Rows\(\d+\)\(\"(\w+)\"\)", self.source_text):
            columns.add(match.group(1))
        for match in re.finditer(r"\.Item\(\"(\w+)\"\)", self.source_text):
            columns.add(match.group(1))
        self.fixture_columns.setdefault(dt_var, set()).update(columns)
        rendered = self._dedupe_declarations(
            f"let {dt_var}: Record<string, string>[] = {data_ident}.map((row) => ({{ ...row }}));"
        )
        out.append(f"{indent}{rendered}")
        self.mapped_ids.append("read.range")
        self.mapped_records.append({"tag": "ReadRange", "selector": None, "rendered": out[-1].strip()})

    def _handle_get_robot_asset(self, element: ET.Element, out: list[str], indent: str) -> None:
        asset_name = element.attrib.get("AssetName", "asset")
        value_child = _find_child_by_suffix(element, ".Value")
        var_name = "asset"
        if value_child is not None and len(value_child) > 0:
            var_name = _strip_brackets(value_child[0].text) or var_name
        env_key = re.sub(r"[^A-Za-z0-9]+", "_", asset_name).strip("_").upper() or "ASSET"
        rendered = self._dedupe_declarations(f"let {var_name} = process.env.UIPATH_ASSET_{env_key} ?? '';")
        out.append(f"{indent}{rendered}")
        self.mapped_ids.append("get.robot.asset")
        self.mapped_records.append({"tag": "GetRobotAsset", "selector": None, "rendered": out[-1].strip()})

    def _handle_multiple_assign(self, element: ET.Element, out: list[str], indent: str) -> None:
        operations_container = _find_child_by_suffix(element, ".AssignOperations")
        if operations_container is None:
            self.structural_count += 1
            return
        for list_container in operations_container:
            for operation in list_container:
                if _local_name(operation.tag) != "AssignOperation":
                    continue
                to_child = _find_child_by_suffix(operation, ".To")
                value_child = _find_child_by_suffix(operation, ".Value")
                var_name = _translate_known_dotnet_calls(
                    _strip_brackets(to_child[0].text if to_child is not None and len(to_child) > 0 else None) or "value"
                )
                raw_value = value_child[0].text if value_child is not None and len(value_child) > 0 else None
                js_value, flagged = _convert_vb_expression(raw_value)
                self._emit_assignment(var_name, js_value, flagged, out, indent)
                self.mapped_ids.append("multiple.assign")
                self.mapped_records.append({"tag": "MultipleAssign", "selector": None, "rendered": out[-1].strip()})

    def _handle_assign(self, element: ET.Element, out: list[str], indent: str) -> None:
        to_child = _find_child_by_suffix(element, ".To")
        value_child = _find_child_by_suffix(element, ".Value")
        var_name = _translate_known_dotnet_calls(
            _strip_brackets(to_child[0].text if to_child is not None and len(to_child) > 0 else None) or "value"
        )
        raw_value = value_child[0].text if value_child is not None and len(value_child) > 0 else None
        js_value, flagged = _convert_vb_expression(raw_value)
        self._emit_assignment(var_name, js_value, flagged, out, indent)
        self.mapped_ids.append("assign")
        self.mapped_records.append({"tag": "Assign", "selector": None, "rendered": out[-1].strip()})

    def _handle_for_each_row(self, element: ET.Element, out: list[str], indent: str) -> None:
        dt_var = _strip_brackets(element.attrib.get("DataTable")) or "dataTable"
        body_container = _find_child_by_suffix(element, ".Body")
        delegate_arg = _find_descendant_by_local_name(body_container, "DelegateInArgument") if body_container is not None else None
        row_var = (delegate_arg.attrib.get("Name") if delegate_arg is not None else None) or "row"
        out.append(f"{indent}for (const {row_var} of {dt_var}) {{")
        self.mapped_ids.append("for.each.row")
        self.mapped_records.append({"tag": "ForEachRow", "selector": None, "rendered": out[-1].strip()})
        for child in element:
            self.walk(child, out, indent + "  ")
        out.append(f"{indent}}}")

    def _handle_foreach(self, element: ET.Element, out: list[str], indent: str) -> None:
        """Generic `ui:ForEach` (loops over any collection, e.g. a JArray) — distinct from `ForEachRow`
        (Excel DataTable-specific). Uses the real DelegateInArgument name for the loop variable."""
        values_expr, flagged = _convert_vb_expression(element.attrib.get("Values"))
        body_container = _find_child_by_suffix(element, ".Body")
        delegate_arg = _find_descendant_by_local_name(body_container, "DelegateInArgument") if body_container is not None else None
        item_var = (delegate_arg.attrib.get("Name") if delegate_arg is not None else None) or "item"
        suffix = "  // VERIFY: VB expression" if flagged else ""
        out.append(f"{indent}for (const {item_var} of {values_expr}) {{{suffix}")
        self.mapped_ids.append("for.each")
        self.mapped_records.append({"tag": "ForEach", "selector": None, "rendered": out[-1].strip()})
        for child in element:
            self.walk(child, out, indent + "  ")
        out.append(f"{indent}}}")

    def _handle_if(self, element: ET.Element, out: list[str], indent: str) -> None:
        condition, flagged = _convert_vb_expression(element.attrib.get("Condition"))
        suffix = "  // VERIFY: VB expression" if flagged else ""
        out.append(f"{indent}if ({condition}) {{{suffix}")
        self.mapped_ids.append("if")
        self.mapped_records.append({"tag": "If", "selector": None, "rendered": f"if ({condition}) {{ ... }}"})
        then_branch = _find_child_by_suffix(element, ".Then")
        if then_branch is not None:
            self.walk(then_branch, out, indent + "  ")
        else_branch = _find_child_by_suffix(element, ".Else")
        if else_branch is not None and list(else_branch):
            out.append(f"{indent}}} else {{")
            self.walk(else_branch, out, indent + "  ")
        out.append(f"{indent}}}")

    def _handle_trycatch(self, element: ET.Element, out: list[str], indent: str) -> None:
        try_container = _find_child_by_suffix(element, ".Try")
        catches_container = _find_child_by_suffix(element, ".Catches")
        finally_container = _find_child_by_suffix(element, ".Finally")
        out.append(f"{indent}try {{")
        if try_container is not None:
            self.walk(try_container, out, indent + "  ")
        out.append(f"{indent}}} catch (error) {{")
        catch_elements = [c for c in catches_container if _local_name(c.tag) == "Catch"] if catches_container is not None else []
        if catch_elements:
            for catch_el in catch_elements:
                self.walk(catch_el, out, indent + "  ")
        else:
            out.append(f"{indent}  throw error;  // no explicit Catch handler in source — rethrow to preserve behavior")
        out.append(f"{indent}}}")
        if finally_container is not None and list(finally_container):
            out.append(f"{indent}finally {{")
            self.walk(finally_container, out, indent + "  ")
            out.append(f"{indent}}}")
        self.mapped_ids.append("try.catch")
        self.mapped_records.append({"tag": "TryCatch", "selector": None, "rendered": "try { ... } catch (error) { ... }"})

    def _handle_napplicationcard(self, element: ET.Element, out: list[str], indent: str) -> None:
        """Modern app/browser launcher (`uix:NApplicationCard`) — the UIAutomationNext equivalent of the
        classic `OpenBrowser` activity. Emits a navigate call from its `TargetApp/@Url` (when present —
        "attach to an already-open instance" cards have no Url and only wrap nested actions), then walks
        into `.Body` to keep processing the nested activities it scopes."""
        target_app_wrapper = _find_child_by_suffix(element, ".TargetApp")
        target_app = _find_descendant_by_local_name(target_app_wrapper, "TargetApp") if target_app_wrapper is not None else None
        url_raw = target_app.attrib.get("Url") if target_app is not None else None
        if url_raw:
            js_value, flagged = _convert_vb_expression(url_raw)
            suffix = "  // VERIFY: VB expression" if flagged else ""
            out.append(f"{indent}await page.goto({js_value});{suffix}")
            self.mapped_ids.append("napplicationcard.navigate")
            self.mapped_records.append({"tag": "NApplicationCard", "selector": None, "rendered": out[-1].strip()})
        else:
            self.structural_count += 1
        body_container = _find_child_by_suffix(element, ".Body")
        if body_container is not None:
            self.walk(body_container, out, indent)

    def _handle_take_screenshot(self, element: ET.Element, out: list[str], indent: str) -> None:
        path_expr, flagged = _convert_vb_expression(element.attrib.get("FileName"))
        suffix = "  // VERIFY: VB expression" if flagged else ""
        out.append(f"{indent}await page.screenshot({{ path: {path_expr} }});{suffix}")
        self.mapped_ids.append("take.screenshot")
        self.mapped_records.append({"tag": "NTakeScreenshot", "selector": None, "rendered": out[-1].strip()})

    def _handle_throw(self, element: ET.Element, out: list[str], indent: str) -> None:
        js_value, flagged = _convert_vb_expression(element.attrib.get("Exception"))
        suffix = "  // VERIFY: VB expression" if flagged else ""
        out.append(f"{indent}throw {js_value};{suffix}")
        self.mapped_ids.append("throw")
        self.mapped_records.append({"tag": "Throw", "selector": None, "rendered": out[-1].strip()})

    def _handle_get_last_downloaded_file(self, element: ET.Element, out: list[str], indent: str) -> None:
        """No direct Playwright equivalent for "wait for a file to finish downloading to a Robot-machine
        folder" — flag it honestly instead of silently dropping the semantic, then still walk its nested
        `.Body` activities (they run real UI steps, e.g. closing a tab, that are independently mappable)."""
        display_name = element.attrib.get("DisplayName", "")
        out.append(f"{indent}// TODO: unmapped activity <GetLastDownloadedFile> {display_name} "
                    f"(waits for a Robot-machine download — consider page.waitForEvent('download') if this project downloads files)".rstrip())
        self.unmatched.append(f"GetLastDownloadedFile ({display_name})")
        body_container = _find_child_by_suffix(element, ".Body")
        if body_container is not None:
            self.walk(body_container, out, indent)

    def _handle_delay(self, element: ET.Element, out: list[str], indent: str) -> None:
        duration_raw = (element.attrib.get("Duration") or "").strip()

        def emit_static(hours: str, minutes: str, seconds: str) -> None:
            ms = round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)
            out.append(f"{indent}await page.waitForTimeout({ms});")
            self.mapped_ids.append("delay")
            self.mapped_records.append({"tag": "Delay", "selector": None, "rendered": out[-1].strip()})

        plain_match = re.match(r"^(\d+):(\d+):(\d+(?:\.\d+)?)$", duration_raw)
        if plain_match:
            emit_static(*plain_match.groups())
            return
        inner = _strip_brackets(duration_raw)
        literal_match = _TIMESPAN_LITERAL_RE.match(inner)
        if literal_match:
            emit_static(*literal_match.groups())
            return
        dynamic_match = _TIMESPAN_DYNAMIC_RE.match(inner)
        if dynamic_match:
            # Duration comes from external test data (e.g. an Excel column) at runtime — best-effort parse
            # of an "HH:MM:SS"-shaped string; flagged for review since the exact source format is not
            # statically known at conversion time.
            expr, _ = _convert_vb_expression(f"[{dynamic_match.group(1)}]")
            out.append(
                f"{indent}await page.waitForTimeout((() => {{ const parts = String({expr}).split(':').map(Number); "
                "return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000; })());  // VERIFY: dynamic Timespan.Parse duration"
            )
            self.mapped_ids.append("delay")
            self.mapped_records.append({"tag": "Delay", "selector": None, "rendered": out[-1].strip()})
            return
        out.append(f"{indent}// TODO: unmapped activity <Delay> Duration={duration_raw}")
        self.unmatched.append(f"Delay ({duration_raw})")

    def _handle_ncheckstate(self, element: ET.Element, out: list[str], indent: str) -> None:
        target = _find_child_by_suffix(element, ".Target")
        selector = None
        if target is not None:
            anchor = _find_descendant_by_local_name(target, "TargetAnchorable")
            if anchor is not None:
                raw = anchor.attrib.get("FullSelectorArgument") or anchor.attrib.get("ScopeSelectorArgument")
                if raw:
                    selector = self.loader.resolve_ui_locator(self.engine, "Element", raw)
        if_exists = _find_child_by_suffix(element, ".IfExists")
        if_not_exists = _find_child_by_suffix(element, ".IfNotExists")
        display_name = element.attrib.get("DisplayName", "condition")
        if selector is None:
            out.append(f"{indent}// TODO: resolve selector for conditional '{display_name}'")
            self.unmatched.append(f"NCheckState ({display_name})")
            selector = "TODO-selector"
        out.append(f"{indent}if (await page.locator('{selector}').isVisible()) {{")
        self.mapped_ids.append("ncheckstate")
        self.mapped_records.append({"tag": "NCheckState", "selector": selector, "rendered": out[-1].strip()})
        if if_exists is not None:
            for child in if_exists:
                self.walk(child, out, indent + "  ")
        out.append(f"{indent}}} else {{")
        if if_not_exists is not None:
            for child in if_not_exists:
                self.walk(child, out, indent + "  ")
        out.append(f"{indent}}}")


def convert_file(
    source_path: Path,
    output_path: Path,
    loader: MapperLoader,
    engine: str = "web",
    strict: bool = False,
    screenshots_dir: str | None = None,
) -> ConversionResult:
    xml_text = source_path.read_text(encoding="utf-8")
    root = ET.fromstring(xml_text)

    walker = ProjectWalker(loader, engine)
    body_lines = walker.walk_root(root)

    if strict and walker.unmatched:
        details = "\n".join(f"  {item}" for item in walker.unmatched)
        raise ValueError(f"Unmapped activities in {source_path}:\n{details}")

    title = (walker.test_name or source_path.stem).replace("\\", "\\\\").replace("'", "\\'")
    if screenshots_dir:
        body_lines = _inject_screenshots(body_lines, screenshots_dir, _slugify(walker.test_name or source_path.stem))
    body = "\n".join(body_lines) or "    // No mapped UiPath actions found."
    generated = (
        "import { test, expect } from '@playwright/test';\n\n"
        f"test.describe('{title}', () => {{\n"
        "  test('migrated UiPath flow', async ({ page }) => {\n"
        f"{body}\n"
        "  });\n"
        "});\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated, encoding="utf-8")
    return ConversionResult(
        source=str(source_path),
        output=str(output_path),
        mapped_actions=len(walker.mapped_ids),
        skipped_lines=walker.structural_count,
        unmatched_lines=len(walker.unmatched),
        action_ids=walker.mapped_ids,
        action_records=walker.mapped_records,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert UiPath Studio (XAML) activities to Playwright TypeScript")
    parser.add_argument("input", type=Path, help="UiPath XAML source file")
    parser.add_argument("-o", "--output", type=Path, help="Generated Playwright spec path")
    parser.add_argument("--client", help="Client mapper overlay name")
    parser.add_argument("--engine", default="web", help="Technology engine (default: web)")
    parser.add_argument("--strict", action="store_true", help="Fail when any activity is unmapped")
    parser.add_argument("--screenshots", help="Directory to capture a page.screenshot() after every UI action (evidence capture)")
    parser.add_argument("--report", type=Path, help="Write compact JSON conversion report")
    parser.add_argument("--agent-input-tokens", type=int, default=0)
    parser.add_argument("--agent-output-tokens", type=int, default=0)
    parser.add_argument("--model", default="claude-sonnet")
    parser.add_argument("--input-rate", type=float, default=3.0)
    parser.add_argument("--output-rate", type=float, default=15.0)
    args = parser.parse_args()

    loader = MapperLoader(client=args.client)
    errors = loader.validate()
    if errors:
        raise SystemExit("Mapper validation failed:\n- " + "\n- ".join(errors))
    output = args.output or Path("output") / f"{args.input.stem}.spec.ts"
    result = convert_file(args.input, output, loader, args.engine, args.strict, args.screenshots)
    token_usage = build_token_report(
        [args.input],
        [output],
        args.agent_input_tokens,
        args.agent_output_tokens,
        args.model,
        args.input_rate,
        args.output_rate,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"file": asdict(result), "tokenUsage": token_usage}, indent=2) + "\n", encoding="utf-8")
    print(
        f"Converted {result.source} -> {result.output} "
        f"({result.mapped_actions} mapped, {result.unmatched_lines} unmatched)"
    )
    print_token_summary(token_usage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
