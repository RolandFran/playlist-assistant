from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomeAssistantPrebuiltImageDeliveryTests(unittest.TestCase):
    @staticmethod
    def normalize_config_version(value: str) -> str:
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value

    @staticmethod
    def config_version() -> str:
        config = (ROOT / "ha_app" / "config.yaml").read_text(encoding="utf-8")
        return next(line.split(":", 1)[1].strip() for line in config.splitlines() if line.startswith("version:"))

    @classmethod
    def release_version_matches(cls, helper_output: str, release_tag: str) -> bool:
        return cls.normalize_config_version(helper_output) == release_tag

    def test_release_workflow_publishes_the_configured_multi_architecture_image(self):
        config = (ROOT / "ha_app" / "config.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "publish-addon-image.yml").read_text(encoding="utf-8")

        self.assertIn('version: "0.1.36"', config)
        self.assertIn('image: "ghcr.io/rolandfran/playlist-assistant"', config)
        self.assertIn("types: [published]", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("release_tag:", workflow)
        self.assertIn('ARCHITECTURES: \'["amd64", "aarch64"]\'', workflow)
        self.assertIn("NORMALIZED_APP_VERSION", workflow)
        self.assertIn("id: version", workflow)
        self.assertIn('echo "version=${NORMALIZED_APP_VERSION}" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("version: ${{ steps.version.outputs.version }}", workflow)
        self.assertNotIn("version: ${{ steps.info.outputs.version }}", workflow)
        self.assertIn("Release tag ${RELEASE_TAG} must exactly match ha_app/config.yaml version", workflow)
        self.assertIn("home-assistant/builder/actions/prepare-multi-arch-matrix@2026.06.0", workflow)
        self.assertIn("home-assistant/builder/actions/build-image@2026.06.0", workflow)
        self.assertIn("home-assistant/builder/actions/publish-multi-arch-manifest@2026.06.0", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("contents: read", workflow)
        self.assertEqual(workflow.count("image-tags: |\n            ${{ needs.prepare.outputs.version }}\n            latest"), 2)
        self.assertIn("version: ${{ needs.prepare.outputs.version }}", workflow)
        self.assertIn("registry_prefix: ${{ steps.image.outputs.registry_prefix }}", workflow)

    def test_quoted_config_version_matches_release_tag(self):
        config_version = self.config_version()
        release_tag = "0.1.36"

        self.assertEqual(config_version, '"0.1.36"')
        self.assertEqual(self.normalize_config_version(config_version), release_tag)

    def test_quoted_helper_output_becomes_normalized_workflow_output(self):
        helper_output = '"0.1.36"'

        self.assertTrue(self.release_version_matches(helper_output, "0.1.36"))

    def test_mismatching_release_tag_still_fails_version_match(self):
        config_version = self.config_version()
        release_tag = "0.1.37"

        self.assertFalse(self.release_version_matches(config_version, release_tag))
