import argparse
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
        self.assertEqual(config.artist_min_gap, 10)
        self.assertEqual(config.rare_weight_factor, 0.5)
        self.assertEqual(config.long_weight_factor, 0.5)

    def test_extreme_weightings_are_valid(self):
        self.assertEqual(
            RuntimeConfig(rare_weight=100, long_weight=0).rare_weight_factor,
            1.0,
        )
        self.assertEqual(
            RuntimeConfig(rare_weight=0, long_weight=100).long_weight_factor,
            1.0,
        )

    def test_invalid_values_are_rejected(self):
        invalid_configs = (
            {"today_size": 0},
            {"artist_min_gap": -1},
            {"rare_weight": -1, "long_weight": 101},
            {"rare_weight": 40, "long_weight": 50},
            {"today_size": True},
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
            "--long-weight", "30",
            "--artist-min-gap", "4",
        ]))

        self.assertEqual(config, RuntimeConfig(25, 70, 30, 4))

    def test_invalid_external_cli_values_are_rejected(self):
        parser = argparse.ArgumentParser()
        add_runtime_config_arguments(parser)
        args = parser.parse_args(["--rare-weight", "70", "--long-weight", "20"])

        with self.assertRaises(RuntimeConfigError):
            runtime_config_from_args(args)
