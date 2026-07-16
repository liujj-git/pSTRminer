# pSTRminer

**Integrated bioinformatic software for genome-wide identification and population-scale evaluation of polymorphic short tandem repeats (STRs).**

pSTRminer provides a complete, reproducible workflow that takes you from a reference genome all the way to a curated, forensically evaluated STR marker set. It runs as both a **graphical desktop application** (Windows / macOS / Linux) and a **command-line tool** for servers and HPC environments.

---

## Contents

- [Quick Start](#quick-start) — download and run in three steps
- [Full Documentation](#full-documentation)
  - [What pSTRminer does](#what-pstrminer-does)
  - [Installation](#installation)
  - [Stage 1 — STR Configuration](#stage-1--str-configuration)
  - [Stage 2 — Polymorphism Screening](#stage-2--polymorphism-screening)
  - [Command-line usage](#command-line-usage)
  - [Output files](#output-files)
  - [Forensic parameters](#forensic-parameters)
  - [External dependencies](#external-dependencies)
  - [Building from source](#building-from-source)
  - [Citation](#citation)
  - [License](#license)

---

# Quick Start

### 1. Download

Grab the latest release for your platform from the [**Releases**](../../releases) page and unzip it.

| Platform | Executable | First run |
|---|---|---|
| **Windows** | `pSTRminer.exe` | Double-click |
| **macOS** | `pSTRminer` | `chmod +x pSTRminer`, then double-click (or run from Terminal) |
| **Linux** | `pSTRminer` | `chmod +x pSTRminer`, then `./pSTRminer` |

The pre-built executables are self-contained and run offline — no Python installation required.

### 2. Launch the GUI

Run the executable with no arguments and the graphical interface opens. You will see two tabs:

- **STR Configuration** (Step 1) — find STRs in a genome and build a HipSTR configuration file
- **Polymorphism Screening** (Step 2) — filter HipSTR output and compute forensic parameters

### 3. Run your analysis

1. In **STR Configuration**, choose a reference genome (a local FASTA file or a UCSC assembly ID for automatic download), point to a TRF binary (or let pSTRminer download it), pick an output folder, and click **Run Configuration**.
2. Run HipSTR yourself on your sequencing data using the configuration file produced in Step 1 (see [External dependencies](#external-dependencies)).
3. In **Polymorphism Screening**, load the HipSTR configuration BED and the HipSTR VCF, set the VCF filtering thresholds, and click **Run Screening**.

The result is a table of candidate STR loci annotated with forensic-genetic parameters, ready for downstream validation and panel design.

> **Prefer the command line?** See [Command-line usage](#command-line-usage).

---

# Full Documentation

## What pSTRminer does

Developing a validated STR panel from raw genomic data normally involves stitching together many separate tools and manual steps. pSTRminer packages that entire process into two self-contained modules behind a single interface.

```
Reference genome (FASTA)
        |
        v
+-----------------------------+
|  Stage 1: STR Configuration |   HipSTR_configuration.sh
|  - TRF-based STR mining      |
|  - builds HipSTR config file |
+-----------------------------+
        |
        v
   (run HipSTR on your WGS data,
    using the configuration file)
        |
        v
+-----------------------------+
| Stage 2: Polymorphism Screen|   Polymorphism.sh
|  - filters the HipSTR VCF     |
|  - computes forensic params   |
|  - ranks candidate loci       |
+-----------------------------+
        |
        v
Curated STR database (CSDB)
```

The alignment and genotyping step in the middle is deliberately delegated to established, widely used tools (HipSTR and its upstream aligners) chosen by the user, keeping pSTRminer modular and interoperable with existing pipelines.

## Installation

### Option A — Pre-built executable (recommended for most users)

Download from the [Releases](../../releases) page as described in [Quick Start](#quick-start). Nothing else to install.

### Option B — From source (Python)

pSTRminer requires **Python >= 3.7**. The GUI uses Tkinter, which ships with most Python installations.

```bash
git clone https://github.com/Sunlab-forensicsysu/pSTRminer.git
cd pSTRminer
pip install .
```

This installs two entry points:

```bash
pstrminer          # unified entry: no args -> GUI, args -> CLI
pstrminer-gui      # launch the GUI directly
```

You can also run without installing:

```bash
python -m pstrminer            # launches the GUI
python -m pstrminer --help     # CLI help
```

> **Note on Tkinter:** if you see `Error: Tkinter is not available`, either install the Tk bindings for your Python (e.g. `sudo apt install python3-tk` on Debian/Ubuntu) or use the command-line interface, which does not require Tkinter.

## Stage 1 — STR Configuration

This stage identifies STRs in a reference genome and produces the configuration file HipSTR needs.

**Inputs**

| Field | Description |
|---|---|
| **Reference Genome Source** | Either *Use a local FASTA file* or *Download from UCSC* (provide a UCSC assembly ID, e.g. `bosTau9`) |
| **TRF (Tandem Repeats Finder)** | Either *Download automatically* or *Use a local TRF binary* |
| **Output folder** | Where the configuration file and intermediate files are written |

**What happens internally**

1. The reference genome is scanned with TRF using default parameters.
2. Raw TRF output is cleaned and reformatted: repeats with a period > 6 bp are removed, low-scoring repeats are discarded, and overlapping STRs are merged into single entries.
3. Each retained region is assigned a unique identifier, and the chromosome, start, end, motif length, repeat number, identifier and motif sequence are extracted to build the HipSTR configuration file.

Click **Run Configuration** to start; progress is shown live in the **Execution Log** panel. **Clear log** resets the panel.

## Stage 2 — Polymorphism Screening

This stage takes HipSTR's genotype calls and turns them into a forensically annotated marker table.

**Inputs**

| Field | Description |
|---|---|
| **HipSTR config BED** | The configuration file produced in Stage 1 |
| **Input VCF** | The VCF produced by running HipSTR on your sequencing data |
| **VCF Filtering** | Enable *Filter the raw VCF* and set the thresholds below |

**Default filtering thresholds**

| Parameter | Default |
|---|---|
| Minimum call quality | 0.9 |
| Max flanking indel rate | 0.15 |
| Max stutter rate | 0.15 |
| Min allele bias | -2 |
| Min strand bias | -2 |

**What happens internally**

1. Low-quality variant calls are removed according to the thresholds above.
2. STR alleles reported by HipSTR in base-pair format are converted to repeat-number format; alleles with the same repeat number but different sequences are given unique labels.
3. Forensic-genetic parameters are computed for every locus (see [Forensic parameters](#forensic-parameters)).

Click **Run Screening**; progress appears in the **Execution Log** panel.

## Command-line usage

The CLI mirrors the two stages and is suited to servers, HPC and scripted pipelines. There are two sub-commands:

```bash
# Stage 1 - build the HipSTR configuration file
pstrminer config --help

# Stage 2 - filter the VCF and compute forensic parameters
pstrminer poly --help
```

Run each sub-command with `--help` to see its full option list. The unified entry point launches the GUI when called with no arguments and switches to CLI mode as soon as a sub-command is supplied.

## Output files

Stage 2 produces a table of candidate STR loci — the **cattle STR database (CSDB)** in the accompanying study — with one row per locus and a column for each computed parameter. This table is the primary deliverable and is ready for downstream validation and panel design.

## Forensic parameters

For each locus, pSTRminer computes the following ten forensic-genetic parameters:

| Abbrev. | Parameter |
|---|---|
| **N** | Total number of observed alleles |
| **Na** | Number of unique allele types |
| **Ho** | Observed heterozygosity |
| **He** | Expected heterozygosity |
| **PIC** | Polymorphism information content |
| **PD** | Power of discrimination |
| **MP** | Match probability (= 1 - PD) |
| **PE_duo** | Probability of exclusion (duos) |
| **PE_trio** | Probability of exclusion (trios) |
| **Ae** | Effective number of alleles |

By default, candidate loci are prioritized by **PIC**, a single, widely used measure of marker informativeness. Because pSTRminer annotates the full parameter set, you can re-rank the curated table by any other parameter — for example by PE_duo or PE_trio for parentage testing — to suit a specific application.

## External dependencies

pSTRminer bundles its own auxiliary scripts, but the following external tools are used in a typical end-to-end workflow:

| Tool | Role | Where |
|---|---|---|
| **TRF (Tandem Repeats Finder)** | STR discovery in Stage 1 | Downloaded automatically or supplied by the user |
| **HipSTR** | Genotyping of the discovered loci from sequencing data | Run by the user between Stage 1 and Stage 2 |

Upstream read processing (quality control, alignment, sorting) is performed with standard tools of your choice before HipSTR (e.g. fastp, bwa, samtools). See the accompanying publication for the exact versions used in the reference study.

## Building from source

To produce a stand-alone executable for your platform:

```bash
pip install .[package]      # installs PyInstaller
pyinstaller pSTRminer.spec
```

The resulting single-file executable appears under `dist/`.

## Citation

If you use pSTRminer in your research, please cite the accompanying publication. Citation details will be added here upon publication.

## License

pSTRminer is released under the **MIT License**. See the [LICENSE](LICENSE) file for the full text.

---

*pSTRminer  |  HipSTR pipeline  |  For academic & forensic research use*
[github.com/Sunlab-forensicsysu/pSTRminer](https://github.com/Sunlab-forensicsysu/pSTRminer)
