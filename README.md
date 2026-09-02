# data_checker — Medical Imaging Dataset Validation Toolkit

Before training a deep learning model (especially for medical image segmentation), run a
"health check" on your dataset: verify that images and labels **correspond one-to-one**, files
are **complete and readable**, **sizes/spacings** are consistent, and **orientations** match.
This toolkit splits these checks into standalone command-line scripts — run whichever one you need.

## Features

- **Four independent scripts**, each targeting one class of problem; run them individually or all at once.
- **Universal reading** via SimpleITK: supports `.mha` / `.mhd` / `.nii` / `.nii.gz` / `.nrrd` and more, with configurable extensions.
- **Dual-format output**: prints a summary to the terminal and saves `.txt` + `.json` reports for archival and CI.
- **Medical-imaging specifics**: beyond shape, it checks `spacing`, the direction cosine matrix, `origin`, and anatomical axis codes (RAI/LPS, etc.).

## Directory layout

```
data_checker/
├── common.py                    # Shared utilities (file discovery, reading, reporting)
├── check_correspondence.py      # ① image-label one-to-one correspondence
├── check_integrity.py           # ② completeness / readability
├── check_size.py                # ③ size / spacing consistency
├── check_orientation.py         # ④ orientation / origin consistency
├── check_all.py                 # Run all four in one go
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

Requires Python ≥ 3.8. Core dependencies: `SimpleITK`, `numpy`.

## Data directory convention

Images and labels live in two separate directories, with **matching filenames (after stripping the extension)**:

```
dataset/
├── image_T2/            # image directory
│   ├── 10000_1000000.mha
│   └── 10001_1000001.mha
└── label/               # label directory (stems match the images)
    ├── 10000_1000000.nii.gz
    └── 10001_1000001.nii.gz
```

`image_T2/10000_1000000.mha` and `label/10000_1000000.nii.gz` are treated as one pair.

## Usage

### Common arguments (shared by all four scripts)

| Argument | Description | Default |
|---|---|---|
| `--image_dir` | Image directory (required) | — |
| `--label_dir` | Label directory (required) | — |
| `--image_ext` | Image file extension | `.mha` |
| `--label_ext` | Label file extension | `.nii.gz` |
| `--limit N` | Check only the first N pairs (quick dry run) | all |
| `--report PREFIX` | Report file prefix (no extension) | `reports/<title>` |
| `--no_save` | Print only, do not save report files | off |

### ① One-to-one correspondence

```bash
python check_correspondence.py --image_dir ./image_T2 --label_dir ./label
```

### ② Completeness / readability

```bash
python check_integrity.py --image_dir ./image_T2 --label_dir ./label
```

### ③ Size / spacing consistency

```bash
python check_size.py --image_dir ./image_T2 --label_dir ./label
```

### ④ Orientation / origin consistency

```bash
python check_orientation.py --image_dir ./image_T2 --label_dir ./label
```

### Run everything at once

```bash
python check_all.py --image_dir ./image_T2 --label_dir ./label
```

Quick dry run over the first 20 pairs, terminal only, no files written:

```bash
python check_all.py --image_dir ./image_T2 --label_dir ./label --limit 20 --no_save
```

## What each script checks

| Script | What it checks |
|---|---|
| `check_correspondence.py` | Image/label counts, whether stems fully align, orphan files (image-only or label-only) |
| `check_integrity.py` | Whether files can be read, empty (all-zero) files, image value range & dtype, label value distribution, foreground ratio, non-integer labels |
| `check_size.py` | Per-pair shape and spacing consistency; whole-dataset size/spacing distribution |
| `check_orientation.py` | Per-pair direction and origin consistency; whole-dataset anatomical axis-code distribution |

## Exit codes

Each script exits with `0` on "pass" and non-zero when problems are found, so you can use `if` in shell scripts or CI.

## FAQ

- **Garbled Chinese in the terminal?** Terminal output follows the system encoding. The `.txt` / `.json` reports are always written as UTF-8 and are unaffected.
- **Using a different data format?** Change `--image_ext` / `--label_ext` — no code changes needed.
- **More than one orientation present?** Mixed orientations are common in medical data. Reorient every volume to a single convention (e.g. RAI or LPS) before training.
