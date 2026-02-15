# Test Plan

> This document describes the testing strategy for ap-create-master.

## Overview

**Project:** ap-create-master
**Primary functionality:** Automated generation of master bias, dark, and flat calibration frames using PixInsight.

## Testing Philosophy

This project follows the [ap-base Testing Standards](https://github.com/jewzaam/ap-base/blob/main/standards/standards/testing.md) and [CLI Testing Standards](https://github.com/jewzaam/ap-base/blob/main/standards/standards/cli-testing.md).

Key testing principles:
- TDD for bug fixes
- Business logic isolation from I/O and CLI
- Integration testing with realistic frame grouping scenarios
- CLI argument mapping verification to prevent attribute bugs

## Test Categories

### Unit Tests

- `test_grouping.py` - Frame grouping by FITS metadata
- `test_script_generator.py` - PixInsight script generation
- `test_master_matching.py` - Master frame matching for flat calibration
- `test_calibrate_masters.py` - Core business logic
- `test_config.py` - Configuration constants

### Integration Tests

- `test_calibrate_masters_integration.py` - End-to-end workflow with frame discovery, grouping, and script generation

### CLI/Main Function Tests

**Purpose:** Verify command-line argument parsing and main() entry point integration.

**Standard:** Follows [CLI Testing Standards](../../standards/standards/cli-testing.md)

**Coverage:**
- Argument name mapping (prevents args.attribute_name typos)
- Each CLI flag individually with call_args verification
- Multiple flags combined
- Error handling (missing PixInsight binary without --script-only)
- Exit code validation

**Pattern:**
- Mocks sys.argv to simulate CLI invocation
- Mocks generate_masters() to isolate argparse
- Verifies call_args to catch attribute name mismatches

**Rationale:** Prevents runtime AttributeError from CLI argument typos. Catches bugs that
linters, type checkers, and unit tests cannot detect.

**Test File:** `tests/test_main.py::TestMainCLI`

**Test Coverage:**
- `test_minimal_execution` - Basic required args
- `test_bias_master_dir_argument` - --bias-master-dir value passing
- `test_dark_master_dir_argument` - --dark-master-dir value passing
- `test_script_dir_argument` - --script-dir value passing
- `test_dryrun_flag` - --dryrun parameter mapping
- `test_debug_flag` - --debug parameter mapping
- `test_quiet_flag` - --quiet parameter mapping
- `test_quiet_short_flag` - -q short form
- `test_script_only_flag` - --script-only prevents execution
- `test_pixinsight_binary_required_without_script_only` - Validation logic
- `test_instance_id_argument` - --instance-id type conversion
- `test_multiple_flags_combined` - Flag interactions
- `test_exception_returns_error_code` - Error handling

## Running Tests

```bash
# Run all tests
make test

# Run CLI tests specifically
pytest tests/test_main.py -v
```

## Changelog

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-02-14 | Add CLI testing documentation and test suite | Implement CLI Testing Standards across all ap-* modules |
