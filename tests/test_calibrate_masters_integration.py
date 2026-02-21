"""
Integration tests for ap_create_master.calibrate_masters module.

Tests real-world workflows and scenarios.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ap_create_master import config
from ap_create_master.calibrate_masters import generate_masters, main


class TestRealWorldWorkflows:
    """Test real-world usage scenarios."""

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_darks_only(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating dark masters only."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        dark_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
            config.NORMALIZED_HEADER_CAMERA: "ATR585M",
            config.NORMALIZED_HEADER_SETTEMP: "-10.00",
            config.NORMALIZED_HEADER_GAIN: "239",
            config.NORMALIZED_HEADER_OFFSET: "150",
            config.NORMALIZED_HEADER_READOUTMODE: "Low Conversion Gain",
        }

        # Mock dark file discovery only
        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "DARK":
                return {
                    "dark1.fits": dark_headers,
                    "dark2.fits": dark_headers,
                    "dark3.fits": dark_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect

        mock_group_files.return_value = {
            (
                "dark",
                "60.0",
                "-10.00",
                "239",
                "150",
                "ATR585M",
                "Low Conversion Gain",
            ): [
                {"path": "dark1.fits", "headers": dark_headers},
                {"path": "dark2.fits", "headers": dark_headers},
                {"path": "dark3.fits", "headers": dark_headers},
            ]
        }

        mock_get_metadata.return_value = {
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
            config.NORMALIZED_HEADER_CAMERA: "ATR585M",
            config.NORMALIZED_HEADER_SETTEMP: "-10.00",
            config.NORMALIZED_HEADER_GAIN: "239",
            config.NORMALIZED_HEADER_OFFSET: "150",
            config.NORMALIZED_HEADER_READOUTMODE: "Low Conversion Gain",
        }

        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        assert len(scripts) == 1
        # Verify script generation was called with empty bias and flat lists
        call_args = mock_generate_script.call_args
        assert call_args[0][1] == []  # bias_groups
        assert len(call_args[0][2]) == 1  # dark_groups
        assert call_args[0][3] == []  # flat_groups

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_bias_and_darks(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating bias and dark masters together."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}
        dark_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
        }

        # Mock both bias and dark discovery
        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "BIAS":
                return {
                    "bias1.fits": bias_headers,
                    "bias2.fits": bias_headers,
                    "bias3.fits": bias_headers,
                }
            elif frame_type == "DARK":
                return {
                    "dark1.fits": dark_headers,
                    "dark2.fits": dark_headers,
                    "dark3.fits": dark_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect

        def group_side_effect(files, frame_type):
            if frame_type == "bias":
                return {
                    ("bias",): [
                        {"path": "bias1.fits", "headers": bias_headers},
                        {"path": "bias2.fits", "headers": bias_headers},
                        {"path": "bias3.fits", "headers": bias_headers},
                    ]
                }
            elif frame_type == "dark":
                return {
                    ("dark", "60.0"): [
                        {"path": "dark1.fits", "headers": dark_headers},
                        {"path": "dark2.fits", "headers": dark_headers},
                        {"path": "dark3.fits", "headers": dark_headers},
                    ]
                }
            return {}

        mock_group_files.side_effect = group_side_effect

        mock_get_metadata.side_effect = [
            {config.NORMALIZED_HEADER_CAMERA: "ATR585M"},  # bias metadata
            {
                config.NORMALIZED_HEADER_CAMERA: "ATR585M",
                config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
            },  # dark metadata
        ]

        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        assert len(scripts) == 1
        # Verify both bias and dark groups were passed
        call_args = mock_generate_script.call_args
        assert len(call_args[0][1]) == 1  # bias_groups
        assert len(call_args[0][2]) == 1  # dark_groups
        assert call_args[0][3] == []  # flat_groups

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.find_matching_master_for_flat")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_all_three_frame_types(
        self,
        mock_generate_script,
        mock_find_master,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating bias, dark, and flat masters together."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        bias_master_dir = str(tmp_path / "bias_masters")
        dark_master_dir = str(tmp_path / "dark_masters")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}
        dark_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
        }
        flat_headers = {
            config.NORMALIZED_HEADER_TYPE: "flat",
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "1.5",
        }

        # Mock all three frame types
        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "BIAS":
                return {
                    "bias1.fits": bias_headers,
                    "bias2.fits": bias_headers,
                    "bias3.fits": bias_headers,
                }
            elif frame_type == "DARK":
                return {
                    "dark1.fits": dark_headers,
                    "dark2.fits": dark_headers,
                    "dark3.fits": dark_headers,
                }
            elif frame_type == "FLAT":
                return {
                    "flat1.fits": flat_headers,
                    "flat2.fits": flat_headers,
                    "flat3.fits": flat_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect

        def group_side_effect(files, frame_type):
            if frame_type == "bias":
                return {
                    ("bias",): [
                        {"path": "bias1.fits", "headers": bias_headers},
                        {"path": "bias2.fits", "headers": bias_headers},
                        {"path": "bias3.fits", "headers": bias_headers},
                    ]
                }
            elif frame_type == "dark":
                return {
                    ("dark", "60.0"): [
                        {"path": "dark1.fits", "headers": dark_headers},
                        {"path": "dark2.fits", "headers": dark_headers},
                        {"path": "dark3.fits", "headers": dark_headers},
                    ]
                }
            elif frame_type == "flat":
                return {
                    ("flat", "B", "2026-01-15"): [
                        {"path": "flat1.fits", "headers": flat_headers},
                        {"path": "flat2.fits", "headers": flat_headers},
                        {"path": "flat3.fits", "headers": flat_headers},
                    ]
                }
            return {}

        mock_group_files.side_effect = group_side_effect

        mock_get_metadata.side_effect = [
            {config.NORMALIZED_HEADER_CAMERA: "ATR585M"},  # bias metadata
            {config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0"},  # dark metadata
            {
                config.NORMALIZED_HEADER_FILTER: "B",
                config.NORMALIZED_HEADER_DATE: "2026-01-15",
            },  # flat metadata
        ]

        mock_find_master.side_effect = ["bias_master.xisf", "dark_master.xisf"]
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(
            input_dir, output_dir, bias_master_dir, dark_master_dir
        )

        assert len(scripts) == 1
        # Verify all three frame types were processed
        call_args = mock_generate_script.call_args
        assert len(call_args[0][1]) == 1  # bias_groups
        assert len(call_args[0][2]) == 1  # dark_groups
        assert len(call_args[0][3]) == 1  # flat_groups

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_multiple_dark_groups(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating darks with multiple exposure times."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        dark_60_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0",
        }
        dark_120_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "120.0",
        }
        dark_300_headers = {
            config.NORMALIZED_HEADER_TYPE: "dark",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "300.0",
        }

        # Mock darks with different exposures
        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "DARK":
                return {
                    "dark_60s_1.fits": dark_60_headers,
                    "dark_60s_2.fits": dark_60_headers,
                    "dark_60s_3.fits": dark_60_headers,
                    "dark_120s_1.fits": dark_120_headers,
                    "dark_120s_2.fits": dark_120_headers,
                    "dark_120s_3.fits": dark_120_headers,
                    "dark_300s_1.fits": dark_300_headers,
                    "dark_300s_2.fits": dark_300_headers,
                    "dark_300s_3.fits": dark_300_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect

        mock_group_files.return_value = {
            ("dark", "60.0"): [
                {"path": "dark_60s_1.fits", "headers": dark_60_headers},
                {"path": "dark_60s_2.fits", "headers": dark_60_headers},
                {"path": "dark_60s_3.fits", "headers": dark_60_headers},
            ],
            ("dark", "120.0"): [
                {"path": "dark_120s_1.fits", "headers": dark_120_headers},
                {"path": "dark_120s_2.fits", "headers": dark_120_headers},
                {"path": "dark_120s_3.fits", "headers": dark_120_headers},
            ],
            ("dark", "300.0"): [
                {"path": "dark_300s_1.fits", "headers": dark_300_headers},
                {"path": "dark_300s_2.fits", "headers": dark_300_headers},
                {"path": "dark_300s_3.fits", "headers": dark_300_headers},
            ],
        }

        mock_get_metadata.side_effect = [
            {config.NORMALIZED_HEADER_EXPOSURESECONDS: "60.0"},
            {config.NORMALIZED_HEADER_EXPOSURESECONDS: "120.0"},
            {config.NORMALIZED_HEADER_EXPOSURESECONDS: "300.0"},
        ]

        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        assert len(scripts) == 1
        # Verify three dark groups were created
        call_args = mock_generate_script.call_args
        assert len(call_args[0][2]) == 3  # dark_groups with 3 different exposures

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_bias_only(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating bias masters only."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}

        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "BIAS":
                return {
                    "bias1.fits": bias_headers,
                    "bias2.fits": bias_headers,
                    "bias3.fits": bias_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect
        mock_group_files.return_value = {
            ("bias",): [
                {"path": "bias1.fits", "headers": bias_headers},
                {"path": "bias2.fits", "headers": bias_headers},
                {"path": "bias3.fits", "headers": bias_headers},
            ]
        }
        mock_get_metadata.return_value = {config.NORMALIZED_HEADER_CAMERA: "ATR585M"}
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        assert len(scripts) == 1
        call_args = mock_generate_script.call_args
        assert len(call_args[0][1]) == 1  # bias_groups
        assert len(call_args[0][2]) == 0  # no dark_groups
        assert len(call_args[0][3]) == 0  # no flat_groups

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.find_matching_master_for_flat")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_flats_only_with_masters(
        self,
        mock_generate_script,
        mock_find_master,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating flat masters using existing bias/dark library."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        bias_master_dir = str(tmp_path / "bias_masters")
        dark_master_dir = str(tmp_path / "dark_masters")
        os.makedirs(input_dir, exist_ok=True)

        flat_headers = {
            config.NORMALIZED_HEADER_TYPE: "flat",
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "1.5",
        }

        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "FLAT":
                return {
                    "flat1.fits": flat_headers,
                    "flat2.fits": flat_headers,
                    "flat3.fits": flat_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect
        mock_group_files.return_value = {
            ("flat", "B", "2026-01-15"): [
                {"path": "flat1.fits", "headers": flat_headers},
                {"path": "flat2.fits", "headers": flat_headers},
                {"path": "flat3.fits", "headers": flat_headers},
            ]
        }
        mock_get_metadata.return_value = {
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
        }
        mock_find_master.side_effect = ["bias_master.xisf", "dark_master.xisf"]
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(
            input_dir, output_dir, bias_master_dir, dark_master_dir
        )

        assert len(scripts) == 1
        call_args = mock_generate_script.call_args
        assert len(call_args[0][1]) == 0  # no bias_groups
        assert len(call_args[0][2]) == 0  # no dark_groups
        assert len(call_args[0][3]) == 1  # flat_groups
        # Verify masters were provided
        flat_group = call_args[0][3][0]
        assert flat_group[2] == "bias_master.xisf"
        assert flat_group[3] == "dark_master.xisf"

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_flats_only_uncalibrated(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating flat masters without calibration (no bias/dark)."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        flat_headers = {
            config.NORMALIZED_HEADER_TYPE: "flat",
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "1.5",
        }

        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "FLAT":
                return {
                    "flat1.fits": flat_headers,
                    "flat2.fits": flat_headers,
                    "flat3.fits": flat_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect
        mock_group_files.return_value = {
            ("flat", "B", "2026-01-15"): [
                {"path": "flat1.fits", "headers": flat_headers},
                {"path": "flat2.fits", "headers": flat_headers},
                {"path": "flat3.fits", "headers": flat_headers},
            ]
        }
        mock_get_metadata.return_value = {
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
        }
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        assert len(scripts) == 1
        call_args = mock_generate_script.call_args
        assert len(call_args[0][3]) == 1  # flat_groups
        # Verify no masters were provided
        flat_group = call_args[0][3][0]
        assert flat_group[2] is None  # no bias master
        assert flat_group[3] is None  # no dark master

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.find_matching_master_for_flat")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_workflow_bias_and_flats(
        self,
        mock_generate_script,
        mock_find_master,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test generating bias and flat masters together (using dark library)."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        bias_master_dir = str(tmp_path / "bias_masters")
        dark_master_dir = str(tmp_path / "dark_masters")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}
        flat_headers = {
            config.NORMALIZED_HEADER_TYPE: "flat",
            config.NORMALIZED_HEADER_FILTER: "B",
            config.NORMALIZED_HEADER_DATE: "2026-01-15",
            config.NORMALIZED_HEADER_EXPOSURESECONDS: "1.5",
        }

        def side_effect(*args, **kwargs):
            frame_type = kwargs.get("filters", {}).get(
                config.NORMALIZED_HEADER_TYPE, ""
            )
            if frame_type == "BIAS":
                return {
                    "bias1.fits": bias_headers,
                    "bias2.fits": bias_headers,
                    "bias3.fits": bias_headers,
                }
            elif frame_type == "FLAT":
                return {
                    "flat1.fits": flat_headers,
                    "flat2.fits": flat_headers,
                    "flat3.fits": flat_headers,
                }
            return {}

        mock_get_filtered.side_effect = side_effect

        def group_side_effect(files, frame_type):
            if frame_type == "bias":
                return {
                    ("bias",): [
                        {"path": "bias1.fits", "headers": bias_headers},
                        {"path": "bias2.fits", "headers": bias_headers},
                        {"path": "bias3.fits", "headers": bias_headers},
                    ]
                }
            elif frame_type == "flat":
                return {
                    ("flat", "B", "2026-01-15"): [
                        {"path": "flat1.fits", "headers": flat_headers},
                        {"path": "flat2.fits", "headers": flat_headers},
                        {"path": "flat3.fits", "headers": flat_headers},
                    ]
                }
            return {}

        mock_group_files.side_effect = group_side_effect

        mock_get_metadata.side_effect = [
            {config.NORMALIZED_HEADER_CAMERA: "ATR585M"},  # bias metadata
            {
                config.NORMALIZED_HEADER_FILTER: "B",
                config.NORMALIZED_HEADER_DATE: "2026-01-15",
            },  # flat metadata
        ]

        mock_find_master.side_effect = ["bias_master.xisf", "dark_master.xisf"]
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(
            input_dir, output_dir, bias_master_dir, dark_master_dir
        )

        assert len(scripts) == 1
        call_args = mock_generate_script.call_args
        assert len(call_args[0][1]) == 1  # bias_groups
        assert len(call_args[0][2]) == 0  # no dark_groups
        assert len(call_args[0][3]) == 1  # flat_groups


class TestOutputStructure:
    """Test output directory structure and file naming."""

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_creates_correct_directory_structure(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test that correct output directories are created."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}
        mock_get_filtered.return_value = {
            "bias1.fits": bias_headers,
            "bias2.fits": bias_headers,
            "bias3.fits": bias_headers,
        }
        mock_group_files.return_value = {
            ("bias",): [
                {"path": "bias1.fits", "headers": bias_headers},
                {"path": "bias2.fits", "headers": bias_headers},
                {"path": "bias3.fits", "headers": bias_headers},
            ]
        }
        mock_get_metadata.return_value = {config.NORMALIZED_HEADER_CAMERA: "ATR585M"}
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(input_dir, output_dir)

        # Verify directory structure
        output_path = Path(output_dir)
        assert (output_path / "master").exists()
        assert (output_path / "logs").exists()

        # Verify script is in logs directory
        assert len(scripts) == 1
        assert "logs" in scripts[0]
        assert scripts[0].endswith("calibrate_masters.js")

    @patch("ap_common.get_filtered_metadata")
    @patch("ap_create_master.calibrate_masters.group_files")
    @patch("ap_create_master.calibrate_masters.get_group_metadata")
    @patch("ap_create_master.calibrate_masters.generate_combined_script")
    def test_script_and_log_have_matching_timestamps(
        self,
        mock_generate_script,
        mock_get_metadata,
        mock_group_files,
        mock_get_filtered,
        tmp_path,
    ):
        """Test that script and log file have matching timestamps."""
        input_dir = str(tmp_path / "input")
        output_dir = str(tmp_path / "output")
        os.makedirs(input_dir, exist_ok=True)

        bias_headers = {config.NORMALIZED_HEADER_TYPE: "bias"}
        mock_get_filtered.return_value = {
            "bias1.fits": bias_headers,
            "bias2.fits": bias_headers,
            "bias3.fits": bias_headers,
        }
        mock_group_files.return_value = {
            ("bias",): [
                {"path": "bias1.fits", "headers": bias_headers},
                {"path": "bias2.fits", "headers": bias_headers},
                {"path": "bias3.fits", "headers": bias_headers},
            ]
        }
        mock_get_metadata.return_value = {config.NORMALIZED_HEADER_CAMERA: "ATR585M"}
        mock_generate_script.return_value = "// Generated script"

        scripts, _ = generate_masters(
            input_dir, output_dir, timestamp="20260127_120000"
        )

        assert len(scripts) == 1
        script_path = Path(scripts[0])

        # Script should have timestamp prefix
        assert script_path.name.startswith("20260127_120000")
        assert "_calibrate_masters.js" in script_path.name

        # Log file path should be passed to generate_combined_script
        call_args = mock_generate_script.call_args
        log_file_arg = call_args[0][4]  # 5th positional argument is log_file
        assert "20260127_120000.log" in log_file_arg


class TestCLI:
    """Test command-line interface."""

    @patch("ap_create_master.calibrate_masters.generate_masters")
    @patch("ap_create_master.calibrate_masters.run_pixinsight")
    def test_cli_script_only_mode(self, mock_run_pi, mock_generate, capsys):
        """Test --script-only flag skips PixInsight execution."""
        mock_generate.return_value = (["/tmp/script.js"], [])

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--script-only",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 0
        mock_generate.assert_called_once()
        mock_run_pi.assert_not_called()

    @patch("ap_create_master.calibrate_masters.generate_masters")
    def test_cli_requires_pixinsight_binary_for_execution(self, mock_generate, capsys):
        """Test that --pixinsight-binary is required without --script-only."""
        mock_generate.return_value = (["/tmp/script.js"], [])

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "pixinsight-binary" in captured.out.lower()

    @patch("ap_create_master.calibrate_masters.generate_masters")
    @patch("ap_create_master.calibrate_masters.run_pixinsight")
    @patch("pathlib.Path.exists")
    def test_cli_executes_pixinsight_when_binary_provided(
        self, mock_exists, mock_run_pi, mock_generate, tmp_path
    ):
        """Test that PixInsight is executed when binary is provided."""
        script_path = str(tmp_path / "logs" / "20260127_120000_calibrate_masters.js")
        mock_generate.return_value = ([script_path], [])
        mock_run_pi.return_value = 0
        mock_exists.return_value = True

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--pixinsight-binary",
            "/opt/PixInsight/bin/PixInsight",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 0
        mock_generate.assert_called_once()
        mock_run_pi.assert_called_once()

    @patch("ap_create_master.calibrate_masters.generate_masters")
    @patch("ap_create_master.calibrate_masters.run_pixinsight")
    @patch("pathlib.Path.exists")
    def test_cli_passes_master_directories(
        self, mock_exists, mock_run_pi, mock_generate, tmp_path
    ):
        """Test that --bias-master-dir and --dark-master-dir are passed through."""
        script_path = str(tmp_path / "logs" / "20260127_120000_calibrate_masters.js")
        mock_generate.return_value = ([script_path], [])
        mock_run_pi.return_value = 0
        mock_exists.return_value = True

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--bias-master-dir",
            "/bias",
            "--dark-master-dir",
            "/darks",
            "--pixinsight-binary",
            "/opt/PixInsight/bin/PixInsight",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 0
        # Check that generate_masters was called with correct arguments
        call_args = mock_generate.call_args
        assert call_args[0][0] == "/input"
        assert call_args[0][1] == "/output"
        assert call_args[0][2] == "/bias"
        assert call_args[0][3] == "/darks"

    @patch("ap_create_master.calibrate_masters.generate_masters")
    def test_cli_handles_no_frames_found(self, mock_generate, capsys):
        """Test CLI handles case where no frames are found."""
        mock_generate.return_value = ([], [])

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--script-only",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No calibration frames found" in captured.out

    @patch("ap_create_master.calibrate_masters.generate_masters")
    @patch("ap_create_master.calibrate_masters.run_pixinsight")
    @patch("pathlib.Path.exists")
    def test_cli_returns_pixinsight_exit_code(
        self, mock_exists, mock_run_pi, mock_generate, tmp_path
    ):
        """Test that CLI returns PixInsight's exit code on failure."""
        script_path = str(tmp_path / "logs" / "20260127_120000_calibrate_masters.js")
        mock_generate.return_value = ([script_path], [])
        mock_run_pi.return_value = 1  # PixInsight failed
        mock_exists.return_value = True

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--pixinsight-binary",
            "/opt/PixInsight/bin/PixInsight",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 1

    @patch("ap_create_master.calibrate_masters.generate_masters")
    def test_cli_handles_exception_gracefully(self, mock_generate, capsys):
        """Test that CLI handles exceptions and returns error code."""
        mock_generate.side_effect = RuntimeError("Simulated error")

        test_args = [
            "ap-create-master",
            "/input",
            "/output",
            "--script-only",
        ]

        with patch.object(sys, "argv", test_args):
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "Simulated error" in captured.err


class TestPixInsightExecution:
    """Test PixInsight execution function."""

    @patch("subprocess.run")
    def test_run_pixinsight_success(self, mock_subprocess, tmp_path):
        """Test successful PixInsight execution."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("// Test script")

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"
        pixinsight_binary.parent.mkdir(parents=True, exist_ok=True)
        pixinsight_binary.write_text("fake binary")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        exit_code = run_pixinsight(
            str(pixinsight_binary),
            str(script_path),
            calibrated_files=[],
            master_files=[],
            instance_id=123,
            force_exit=True,
        )

        assert exit_code == 0
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "--automation-mode" in cmd
        assert "-n=123" in cmd
        assert f"-r={script_path}" in cmd
        assert "--force-exit" in cmd

    @patch("subprocess.run")
    def test_run_pixinsight_failure(self, mock_subprocess, tmp_path):
        """Test PixInsight execution with non-zero exit code."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("// Test script")

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"
        pixinsight_binary.parent.mkdir(parents=True, exist_ok=True)
        pixinsight_binary.write_text("fake binary")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error: Something went wrong"
        mock_subprocess.return_value = mock_result

        exit_code = run_pixinsight(
            str(pixinsight_binary),
            str(script_path),
            calibrated_files=[],
            master_files=[],
        )

        assert exit_code == 1

    @patch("subprocess.run")
    def test_run_pixinsight_without_force_exit(self, mock_subprocess, tmp_path):
        """Test PixInsight execution without force-exit flag."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("// Test script")

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"
        pixinsight_binary.parent.mkdir(parents=True, exist_ok=True)
        pixinsight_binary.write_text("fake binary")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        exit_code = run_pixinsight(
            str(pixinsight_binary),
            str(script_path),
            calibrated_files=[],
            master_files=[],
            force_exit=False,
        )

        assert exit_code == 0
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "--force-exit" not in cmd

    def test_run_pixinsight_binary_not_found(self, tmp_path):
        """Test error when PixInsight binary doesn't exist."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("// Test script")

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"

        with pytest.raises(FileNotFoundError, match="PixInsight binary not found"):
            run_pixinsight(
                str(pixinsight_binary),
                str(script_path),
                calibrated_files=[],
                master_files=[],
            )

    def test_run_pixinsight_script_not_found(self, tmp_path):
        """Test error when script file doesn't exist."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"
        pixinsight_binary.parent.mkdir(parents=True, exist_ok=True)
        pixinsight_binary.write_text("fake binary")

        with pytest.raises(FileNotFoundError, match="Script not found"):
            run_pixinsight(
                str(pixinsight_binary),
                str(script_path),
                calibrated_files=[],
                master_files=[],
            )

    @patch("subprocess.run")
    def test_run_pixinsight_subprocess_exception(self, mock_subprocess, tmp_path):
        """Test handling of subprocess exceptions."""
        from ap_create_master.calibrate_masters import run_pixinsight

        script_path = tmp_path / "logs" / "script.js"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("// Test script")

        pixinsight_binary = tmp_path / "bin" / "PixInsight.exe"
        pixinsight_binary.parent.mkdir(parents=True, exist_ok=True)
        pixinsight_binary.write_text("fake binary")

        mock_subprocess.side_effect = OSError("Permission denied")

        with pytest.raises(OSError, match="Permission denied"):
            run_pixinsight(
                str(pixinsight_binary),
                str(script_path),
                calibrated_files=[],
                master_files=[],
            )
