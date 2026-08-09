import argparse
import contextlib
import io
import unittest

from runtime_config import (
    RuntimeConfig,
    RuntimeConfigError,
    add_runtime_config_arguments,
    get_runtime_config,
    runtime_config_from_args,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_defaults_match_the_project_configuration(self):
        config = get_runtime_config()

        self.assertEqual(config.today_size, 200)
        self.assertEqual(config.rare_weight, 50)
        self.assertEqual(config.long_weight, 50)
        self.assertEqual(config.artist_gap, 10)
        self.assertEqual(config.history_poll_minutes, 90)
        self.assertTrue(config.today_schedule_enabled)
        self.assertEqual(config.today_schedule_time, "04:00")
        self.assertEqual(config.rare_weight_factor, 0.5)
        self.assertEqual(config.long_weight_factor, 0.5)

    def test_extreme_weightings_are_valid(self):
        self.assertEqual(RuntimeConfig(rare_weight=100).long_weight, 0)
        self.assertEqual(RuntimeConfig(rare_weight=0).long_weight, 100)
        self.assertEqual(RuntimeConfig(rare_weight=100).rare_weight_factor, 1.0)
        self.assertEqual(RuntimeConfig(rare_weight=0).long_weight_factor, 1.0)

    def test_long_weight_is_derived_from_rare_weight(self):
        config = RuntimeConfig(rare_weight=70)

        self.assertEqual(config.rare_weight, 70)
        self.assertEqual(config.long_weight, 30)

    def test_long_weight_cannot_be_set_independently(self):
        with self.assertRaises(TypeError):
            RuntimeConfig(long_weight=30)

    def test_invalid_values_are_rejected(self):
        invalid_configs = (
            {"today_size": 0},
            {"artist_gap": -1},
            {"rare_weight": -1},
            {"rare_weight": 101},
            {"today_size": True},
            {"today_schedule_enabled": 1},
            {"today_schedule_time": "4:00"},
            {"today_schedule_time": "24:00"},
            {"today_schedule_time": "04:60"},
        )

        for values in invalid_configs:
            with self.subTest(values=values):
                with self.assertRaises(RuntimeConfigError):
                    RuntimeConfig(**values)

    def test_external_cli_values_are_validated_by_runtime_config(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)

        config = runtime_config_from_args(parser.parse_args([
            "--today-size", "25",
            "--rare-weight", "70",
            "--artist-gap", "4",
        ]))

        self.assertEqual(config, RuntimeConfig(25, 70, 4))
        self.assertEqual(config.long_weight, 30)

    def test_legacy_artist_min_gap_cli_alias_maps_to_artist_gap(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)

        config = runtime_config_from_args(parser.parse_args([
            "--artist-min-gap", "4",
        ]))

        self.assertEqual(config.artist_gap, 4)

    def test_artist_gap_cli_spellings_produce_the_same_configuration(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)

        preferred = runtime_config_from_args(
            parser.parse_args(["--artist-gap", "4"])
        )
        legacy = runtime_config_from_args(
            parser.parse_args(["--artist-min-gap", "4"])
        )

        self.assertEqual(preferred.artist_gap, legacy.artist_gap)

    def test_invalid_external_cli_values_are_rejected(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)
        args = parser.parse_args(["--rare-weight", "101"])

        with self.assertRaises(RuntimeConfigError):
            runtime_config_from_args(args)

    def test_long_weight_is_not_a_cli_option(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--long-weight", "30"])
