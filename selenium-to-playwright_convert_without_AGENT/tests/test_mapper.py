from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from convert import convert_file
from mapper_loader import MapperLoader
from token_usage import build_token_report


class MapperTests(unittest.TestCase):
    def test_base_mappers_validate(self) -> None:
        self.assertEqual(MapperLoader().validate(), [])

    def test_client_override_changes_button_priority(self) -> None:
        loader = MapperLoader(client="example-saucedemo")
        self.assertEqual(loader.property_priority("web", "Button")[:2], ["testId", "id"])

    def test_first_matching_action_renders_locator(self) -> None:
        action = MapperLoader().match_action(
            "web", 'driver.findElement(By.id("login-button")).click();'
        )
        self.assertIsNotNone(action)
        self.assertEqual(action["id"], "element.direct.click")
        self.assertEqual(action["rendered"], "await page.locator('#login-button').click();")

    def test_fixture_conversion(self) -> None:
        source = ROOT / "input" / "LoginFlow.java"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "LoginFlow.spec.ts"
            result = convert_file(source, output, MapperLoader())
            generated = output.read_text(encoding="utf-8")
        self.assertEqual(result.mapped_actions, 6)
        self.assertIn("await page.goto(\"https://www.saucedemo.com\");", generated)
        self.assertIn("await expect(loginButton).toBeVisible();", generated)

    def test_token_report_separates_python_and_agent_usage(self) -> None:
        report = build_token_report([], [], 2_000_000, 1_000_000, input_rate_per_million=3, output_rate_per_million=15)
        self.assertEqual(report["migrationConversion"]["billableInputTokens"], 0)
        self.assertEqual(report["optionalAgentAssistance"]["totalTokens"], 3_000_000)
        self.assertEqual(report["totalEstimatedCostUsd"], 21.0)


if __name__ == "__main__":
    unittest.main()