from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from convert import ProjectWalker, convert_file
from mapper_loader import MapperLoader
from token_usage import build_token_report


class MapperTests(unittest.TestCase):
    def test_base_mappers_validate(self) -> None:
        self.assertEqual(MapperLoader().validate(), [])

    def test_client_override_changes_text_field_priority(self) -> None:
        loader = MapperLoader(client="example-saucedemo")
        self.assertEqual(loader.property_priority("web", "TextField")[:2], ["testid", "automationid"])

    def test_first_matching_action_renders_locator(self) -> None:
        loader = MapperLoader()
        element = ET.fromstring(
            "<ui:Click xmlns:ui='http://schemas.uipath.com/workflow/activities' "
            "Selector=\"&lt;webctrl id='login-button' tag='INPUT' /&gt;\" DisplayName=\"Click 'login-button'\" />"
        )
        action = loader.action_for_tag("web", "Click", element.attrib)
        self.assertIsNotNone(action)
        self.assertEqual(action["id"], "click")
        walker = ProjectWalker(loader)
        selector = walker._resolve_selector(action, element)
        rendered = loader.render("web", action, element.attrib, selector)
        self.assertEqual(rendered, "await page.locator('#login-button').click();")

    def test_classic_fixture_conversion(self) -> None:
        source = ROOT / "input" / "LoginFlow.xaml"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "LoginFlow.spec.ts"
            result = convert_file(source, output, MapperLoader())
            generated = output.read_text(encoding="utf-8")
        self.assertEqual(result.mapped_actions, 7)
        self.assertEqual(result.unmatched_lines, 0)
        self.assertIn("await page.goto('https://www.saucedemo.com');", generated)
        self.assertIn("await page.locator('#user-name').fill('standard_user');", generated)
        self.assertIn("let isProductsVisible = undefined;", generated)
        self.assertIn("isProductsVisible = await page.locator('text=Products').isVisible();", generated)
        self.assertIn("expect(isProductsVisible).toBeTruthy();", generated)

    def test_modern_fixture_conversion(self) -> None:
        source = ROOT / "input" / "ModernAppFlow.xaml"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ModernAppFlow.spec.ts"
            result = convert_file(source, output, MapperLoader())
            generated = output.read_text(encoding="utf-8")
        self.assertEqual(result.unmatched_lines, 0)
        # test title taken from ra:StartTest's TestName, not the file stem
        self.assertIn("test.describe('Modern App Flow'", generated)
        # MultipleAssign reassigns the pre-declared Sequence.Variables variable (no redeclaration)
        self.assertIn("let Username = '';", generated)
        self.assertIn("Username = \"standard_user\";", generated)
        # NTypeInto with Target-based selector
        self.assertIn("await page.locator('#USERNAME_FIELD-inner').fill(Username);", generated)
        # NClick with Target-based selector
        self.assertIn("await page.locator('#LOGIN_LINK').click();", generated)
        # CommentOut contents must NOT appear
        self.assertNotIn("ShouldNotAppear", generated)
        # NCheckState if/else branches
        self.assertIn("if (await page.locator('text=Avatar').isVisible()) {", generated)
        self.assertIn("Profile icon visible", generated)
        self.assertIn("Profile icon not available", generated)

    def test_token_report_separates_python_and_agent_usage(self) -> None:
        report = build_token_report([], [], 2_000_000, 1_000_000, input_rate_per_million=3, output_rate_per_million=15)
        self.assertEqual(report["migrationConversion"]["billableInputTokens"], 0)
        self.assertEqual(report["optionalAgentAssistance"]["totalTokens"], 3_000_000)
        self.assertEqual(report["totalEstimatedCostUsd"], 21.0)


if __name__ == "__main__":
    unittest.main()
