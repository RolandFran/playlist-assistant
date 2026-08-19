from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomeAssistantPrebuiltImageDeliveryTests(unittest.TestCase):
    def test_release_workflow_publishes_the_configured_multi_architecture_image(self):
        config = (ROOT / "ha_app" / "config.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "publish-addon-image.yml").read_text(encoding="utf-8")

        self.assertIn('version: "0.1.36"', config)
        self.assertIn('image: "ghcr.io/rolandfran/playlist-assistant"', config)
        self.assertIn("types: [published]", workflow)
        self.assertIn('ARCHITECTURES: \'["amd64", "aarch64"]\'', workflow)
        self.assertIn("Release tag ${RELEASE_TAG} must exactly match ha_app/config.yaml version", workflow)
        self.assertIn("home-assistant/builder/actions/prepare-multi-arch-matrix@2026.06.0", workflow)
        self.assertIn("home-assistant/builder/actions/build-image@2026.06.0", workflow)
        self.assertIn("home-assistant/builder/actions/publish-multi-arch-manifest@2026.06.0", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("image-tags: |\n            ${{ needs.prepare.outputs.version }}", workflow)
        self.assertIn("registry_prefix: ${{ steps.image.outputs.registry_prefix }}", workflow)
