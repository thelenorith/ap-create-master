# ap-create-master

[![Test](https://github.com/jewzaam/ap-create-master/actions/workflows/test.yml/badge.svg)](https://github.com/jewzaam/ap-create-master/actions/workflows/test.yml) [![Coverage](https://github.com/jewzaam/ap-create-master/actions/workflows/coverage.yml/badge.svg)](https://github.com/jewzaam/ap-create-master/actions/workflows/coverage.yml) [![Lint](https://github.com/jewzaam/ap-create-master/actions/workflows/lint.yml/badge.svg)](https://github.com/jewzaam/ap-create-master/actions/workflows/lint.yml) [![Format](https://github.com/jewzaam/ap-create-master/actions/workflows/format.yml/badge.svg)](https://github.com/jewzaam/ap-create-master/actions/workflows/format.yml) [![Type Check](https://github.com/jewzaam/ap-create-master/actions/workflows/typecheck.yml/badge.svg)](https://github.com/jewzaam/ap-create-master/actions/workflows/typecheck.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Automated generation of master bias, dark, and flat calibration frames for PixInsight.

## What It Does

- Discovers and groups calibration frames by FITS keywords
- Generates master bias, dark, and flat frames using PixInsight ImageIntegration
- Calibrates flats with bias/dark masters using ImageCalibration with dark optimization
- Runs completely hands-off from the command line

## Documentation

This tool is part of the astrophotography pipeline. For comprehensive documentation including workflow guides and integration with other tools, see:

- **[Pipeline Overview](https://github.com/jewzaam/ap-base/blob/main/docs/index.md)** - Full pipeline documentation
- **[Workflow Guide](https://github.com/jewzaam/ap-base/blob/main/docs/workflow.md)** - Detailed workflow with diagrams
- **[ap-create-master Reference](https://github.com/jewzaam/ap-base/blob/main/docs/tools/ap-create-master.md)** - API reference for this tool

## Installation

### Development

```bash
make install-dev
```

### From Git

```bash
pip install git+https://github.com/jewzaam/ap-create-master.git
```

## Quick Start

**Generate bias/dark masters:**
```bash
python -m ap_create_master /path/to/calibration /path/to/output \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"
```

**Generate flat masters using existing library:**
```bash
python -m ap_create_master /path/to/flats /path/to/output \
    --bias-master-dir /path/to/bias/library \
    --dark-master-dir /path/to/dark/library \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"
```

**Generate scripts without executing:**
```bash
python -m ap_create_master /path/to/calibration /path/to/output --script-only
```

**Dry run to see what would be generated:**
```bash
python -m ap_create_master /path/to/calibration /path/to/output --dryrun
```

**With debug output:**
```bash
python -m ap_create_master /path/to/calibration /path/to/output --debug \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"
```

**Quiet mode (minimal output):**
```bash
python -m ap_create_master /path/to/calibration /path/to/output --quiet \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"
```

## Important Limitation

Masters created in a run are **not used** for flat calibration in that same run. To calibrate flats, you must use existing masters from a library or run in stages:

```bash
# Stage 1: Generate bias/darks
python -m ap_create_master ./bias_and_darks ./masters \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"

# Stage 2: Generate flats using the masters from stage 1
python -m ap_create_master ./flats ./output \
    --bias-master-dir ./masters/master \
    --dark-master-dir ./masters/master \
    --pixinsight-binary "C:\Program Files\PixInsight\bin\PixInsight.exe"
```

This design keeps each run focused on a single task and makes master matching explicit and predictable.

## Output Structure

```
output_dir/
├── master/          # Master calibration frames (.xisf)
└── logs/            # Generated scripts and execution logs
```

Masters are named with metadata for traceability:
- `masterBias_INSTRUME_<camera>_SETTEMP_<temp>_GAIN_<gain>_OFFSET_<offset>_READOUTM_<mode>.xisf`
- `masterDark_<above>_EXPOSURE_<seconds>.xisf`
- `masterFlat_<above>_DATE-OBS_<date>_FILTER_<filter>.xisf`

## Requirements

- Python 3.9+
- PixInsight installed
- `ap-common` package (installed automatically)

Frames must have proper FITS keywords:
- `IMAGETYP`: Frame type (`bias`, `dark`, `flat`)
- `INSTRUME`: Camera model
- `SET-TEMP` or `SETTEMP`: Sensor temperature
- `GAIN`: Gain setting
- `OFFSET`: Offset setting
- `READOUTMODE` or `READOUTM`: Readout mode
- `EXPOSURE` or `EXPTIME`: Exposure time (for darks/flats)
- `DATE-OBS`: Observation date (for flats)
- `FILTER`: Filter name (for flats)

## Command Line Options

```
python -m ap_create_master [-h] [--bias-master-dir DIR] [--dark-master-dir DIR]
                                [--script-dir DIR] [--pixinsight-binary PATH]
                                [--instance-id ID] [--no-force-exit] [--script-only]
                                [--dryrun] [--debug] [--quiet]
                                input_dir output_dir

positional arguments:
  input_dir             Input directory containing calibration frames
  output_dir            Base output directory

optional arguments:
  -h, --help            Show help message and exit
  --bias-master-dir     Directory containing bias master library (for flat calibration)
  --dark-master-dir     Directory containing dark master library (for flat calibration)
  --script-dir          Directory for scripts and logs (default: output_dir/logs)
  --pixinsight-binary   Path to PixInsight binary (required unless --script-only)
  --instance-id         PixInsight instance ID (default: 123)
  --no-force-exit       Keep PixInsight open after execution completes
  --script-only         Generate scripts only, do not execute PixInsight
  --dryrun              Show what would be done without executing
  --debug               Enable debug logging
  --quiet, -q           Suppress progress output
```

Run `python -m ap_create_master --help` for full details.

## How It Works

### Frame Grouping

Frames are automatically grouped by FITS keywords to ensure only compatible frames are combined:

- **Bias**: Grouped by camera, temperature, gain, offset, readout mode
- **Dark**: Grouped by all bias criteria plus exposure time
- **Flat**: Grouped by all bias criteria plus observation date and filter

### Master Generation

- **Bias/Dark**: Integrated using ImageIntegration with no normalization
- **Flat**: Optionally calibrated with bias/dark masters using ImageCalibration with dark optimization, then integrated using multiplicative normalization

### Master Library Matching

When searching for bias/dark masters in library directories:
- Masters are matched by instrument settings only (camera, temperature, gain, offset, readout mode)
- Date and filter are ignored (they vary per flat group)
- Dark masters with lower or equal exposure time are preferred
- If no lower exposure dark exists, the next higher exposure is used

## Troubleshooting

**No frames found:**
- Verify files have `.fit` or `.fits` extensions
- Check that `IMAGETYP` FITS keyword is set correctly (`bias`, `dark`, or `flat`)
- Ensure the input directory path is correct

**PixInsight not found:**
- Verify the `--pixinsight-binary` path is correct
- On Windows: `C:\Program Files\PixInsight\bin\PixInsight.exe`
- On Linux/Mac: `/opt/PixInsight/bin/PixInsight` or `/Applications/PixInsight/bin/PixInsight`

**No matching master found for flat calibration:**
- Check that bias/dark masters have matching instrument settings in their FITS headers
- Masters must match: `INSTRUME`, `SETTEMP`, `GAIN`, `OFFSET`, `READOUTM`
- Date and filter differences are expected

**PixInsight execution fails:**
- Check the generated script at `<output_dir>/logs/<timestamp>_calibrate_masters.js`
- Review the execution log at `<output_dir>/logs/<timestamp>.log`