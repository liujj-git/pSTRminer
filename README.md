# pSTRminer

**Integrated bioinformatic software for genome-wide identification and population-scale evaluation of polymorphic short tandem repeats (STRs).**

pSTRminer provides a complete, reproducible workflow that takes you from a reference genome all the way to a curated, forensically evaluated STR marker set. It runs as both a **graphical desktop application** and a **command-line tool** for servers and HPC environments.

> **Platform:** pSTRminer runs on **Linux (x86-64)**. See [Platform support](#platform-support).

---

## Contents

- [Quick Start](#quick-start)
- [Platform support](#platform-support)
- [What pSTRminer does](#what-pstrminer-does)
- [Installation](#installation)
- [Step 1 — STR Configuration](#step-1--str-configuration)
- [Step 2 — Polymorphism Screening](#step-2--polymorphism-screening)
- [Command-line usage](#command-line-usage)
- [Output files](#output-files)
- [Forensic parameters](#forensic-parameters)
- [Dependencies](#dependencies)
- [Building from source](#building-from-source)
- [Citation](#citation)
- [License](#license)

---

# Quick Start

### 1. Download

Download the latest release from the [**Releases**](../../releases) page and unpack it:

```bash
tar -xzf pSTRminer-1.0.1-linux-x86_64.tar.gz
cd pSTRminer
chmod +x pSTRminer
```

The release is a self-contained bundle — no Python installation required. Keep the folder intact; the executable loads its bundled files from alongside itself.

### 2. Launch the GUI

Run the executable with no arguments:

```bash
./pSTRminer
```

The graphical interface opens with two tabs:

- **STR Configuration** (Step 1) — find STRs in a genome and build a HipSTR configuration file
- **Polymorphism Screening** (Step 2) — filter HipSTR output and compute forensic parameters

> The GUI needs a graphical display. On a headless server or compute node, use the [command-line interface](#command-line-usage), or connect with X11 forwarding (`ssh -X`).

### 3. Run your analysis

1. In **STR Configuration**, choose a reference genome (a local FASTA file, or a UCSC assembly ID for automatic download), point to a TRF binary (or let pSTRminer download it), pick an output folder, and click **Run Configuration**.
2. Run HipSTR yourself on your sequencing data, using the configuration file produced in Step 1 (see [Dependencies](#dependencies)).
3. In **Polymorphism Screening**, load the HipSTR configuration BED and the HipSTR VCF, set the filtering thresholds, and click **Run Screening**.

The result is a table of candidate STR loci annotated with forensic-genetic parameters, ready for downstream validation and panel design.

---

# Platform support

| Platform | Status |
|---|---|
| **Linux (x86-64)** | Supported and tested |
| macOS | Not supported |
| Windows | Not supported |

pSTRminer's pipeline is built on Bash scripts and on the Linux x86-64 build of Tandem Repeats Finder (`trf409.legacylinux64`), and Step 1 requires Linux command-line tools such as `bedtools`. Windows and macOS are therefore not supported at present.

Windows users can run pSTRminer under WSL2 (Windows Subsystem for Linux) with a standard Ubuntu distribution, though this configuration has not been formally tested.

---

# What pSTRminer does

Developing a validated STR panel from raw genomic data normally involves stitching together many separate tools and manual steps. pSTRminer packages that entire process into two self-contained steps behind a single interface.

```
Reference genome (FASTA)
        |
        v
+------------------------------+
|  Step 1: STR Configuration  |   HipSTR_configuration.sh
|  - TRF-based STR mining      |
|  - builds HipSTR config file |
+------------------------------+
        |
        v
   (run HipSTR on your WGS data,
    using the configuration file)
        |
        v
+------------------------------+
| Step 2: Polymorphism Screen |   Polymorphism.sh
|  - filters the HipSTR VCF    |
|  - computes forensic params  |
|  - ranks candidate loci      |
+------------------------------+
        |
        v
Curated STR database (CSDB)
```

The alignment and genotyping step in the middle is deliberately delegated to established, widely used tools (HipSTR and its upstream aligners) chosen by the user, keeping pSTRminer modular and interoperable with existing pipelines.

---

# Installation

### Option A — Pre-built release (recommended)

Download and unpack from the [Releases](../../releases) page as shown in [Quick Start](#quick-start). Nothing else to install beyond the [external dependencies](#dependencies).

### Option B — From source

pSTRminer requires **Python >= 3.7**. The GUI uses Tkinter, which ships with most Python installations.

```bash
git clone https://github.com/liujj-git/pSTRminer.git
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

---

# Step 1 — STR Configuration

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

Click **Run Configuration** to start; progress is shown live in the **Execution Log** panel.

> Step 1 scans an entire genome with TRF and is compute-intensive — expect hours of runtime on a mammalian genome.

**Output** (in `<output>/reference_genome/`):

| File | Description |
|---|---|
| `<genome>.configuration.bed` | All STR regions |
| `<genome>.configuration.DitoHex.bed` | Di- to hexanucleotide repeats only — this is the file used by HipSTR and in Step 2 |

---

# Step 2 — Polymorphism Screening

This stage takes HipSTR's genotype calls and turns them into a forensically annotated marker table.

**Inputs**

| Field | Description |
|---|---|
| **HipSTR config BED** | The `.DitoHex.bed` file produced in Step 1 |
| **Input VCF** | The VCF produced by running HipSTR on your sequencing data (plain or `.gz`) |
| **Filtering mode** | *Mode T* — filter the raw VCF first (default); *Mode F* — the VCF is already filtered |

**Default filtering thresholds (Mode T)**

| Parameter | Default | Applied to |
|---|---|---|
| Minimum call quality | 0.9 | `Q` |
| Max flanking indel rate | 0.15 | `DFLANKINDEL / DP` |
| Max stutter rate | 0.15 | `DSTUTTER / DP` |
| Min allele bias | -2 | `AB` |
| Min strand bias | -2 | `FS` |

A call that fails any active threshold, or whose `PDP` field reports zero depth for either allele, has its genotype set to missing and is excluded from all downstream calculations.

**What happens internally**

1. Low-quality genotype calls are removed according to the thresholds above.
2. STR alleles reported by HipSTR in base-pair format are converted to repeat-number format; alleles with the same repeat number but different sequences are given unique labels.
3. Forensic-genetic parameters are computed for every locus (see [Forensic parameters](#forensic-parameters)).

Click **Run Screening**; progress appears in the **Execution Log** panel.

---

# Command-line usage

The CLI mirrors the two stages and is suited to servers, HPC and scripted pipelines. The unified entry point launches the GUI when called with no arguments, and switches to CLI mode as soon as a sub-command is supplied.

### Step 1

```bash
# Download bosTau9 from UCSC and generate the configuration
./pSTRminer config -o ./results -R bosTau9

# Use a local reference FASTA
./pSTRminer config -o ./results --reference /data/bosTau9.fa

# Use a local TRF binary (offline or firewalled machines)
./pSTRminer config -o ./results --reference /data/bosTau9.fa --trf /opt/trf409.legacylinux64
```

### Step 2

```bash
# Mode T: filter the raw HipSTR VCF, then compute parameters
./pSTRminer poly \
  -o ./results \
  -C ./results/reference_genome/bosTau9.configuration.DitoHex.bed \
  -I hipstr_output.vcf.gz \
  -O my_study \
  -F T \
  --min-call-qual 0.9 \
  --max-call-flank-indel 0.15 \
  --max-call-stutter 0.15 \
  --min-call-allele-bias -2 \
  --min-call-strand-bias -2

# Mode F: the VCF is already filtered
./pSTRminer poly -o ./results -C config.DitoHex.bed -I pre_filtered.vcf -O my_study -F F
```

Run any sub-command with `--help` for the full option list.

---

# Output files

Step 2 writes the following into the output directory:

| File | Description |
|---|---|
| `<prefix>.filtered.vcf` | Quality-filtered VCF (Mode T only) |
| `<prefix>.allele_sequence.txt` | Allele sequences and their copy numbers |
| `<prefix>.GT.copynumber.txt` | Copy-number genotype matrix |
| `<prefix>.forensic_parameters.txt` | All forensic parameters, one row per locus |
| `<prefix>.allele_freq.txt` | Allele frequencies per locus |
| `<prefix>.analysis_summary.txt` | Per-run summary written by the R pipeline |
| `<prefix>.analysis_report.txt` | Run report: inputs, thresholds and output inventory |

`<prefix>.forensic_parameters.txt` — the **cattle STR database (CSDB)** in the accompanying study — is the primary deliverable, ready for downstream validation and panel design.

---

# Forensic parameters

For each locus, pSTRminer computes the following ten forensic-genetic parameters:

Columns appear in `<prefix>.forensic_parameters.txt` in this order:

| Abbrev. | Parameter |
|---|---|
| **N** | Total number of observed alleles |
| **Na** | Number of unique allele types |
| **Ho** | Observed heterozygosity |
| **He** | Expected heterozygosity (Nei's unbiased estimator, with the N/(N−1) correction) |
| **MP** | Match probability |
| **PD** | Power of discrimination (= 1 − MP) |
| **PE2** | Probability of exclusion (duos) |
| **PE3** | Probability of exclusion (trios) |
| **PIC** | Polymorphism information content |
| **Ae** | Effective number of alleles (= 1 / Σpᵢ²) |

By default, candidate loci are prioritized by **PIC**, a single, widely used measure of marker informativeness. Because pSTRminer annotates the full parameter set, you can re-rank the curated table by any other parameter — for example by PE2 or PE3 for parentage testing — to suit a specific application.

---

# Dependencies

pSTRminer bundles all of its own auxiliary scripts, including its VCF filter. The following must be available on the system.

### Step 1

| Requirement | Notes |
|---|---|
| `bash` | The pipeline scripts are Bash-based |
| `python2` | Required by the bundled HipSTR-references helper scripts |
| `bedtools` | Interval sorting, merging and windowing |
| `faidx` | From [pyfaidx](https://github.com/mdshw5/pyfaidx); splits the genome per chromosome |
| `wget`, `git` | Download of the reference genome and, if needed, of TRF |
| **TRF** | Downloaded automatically on first run, or supplied with `--trf` |

### Step 2

| Requirement | Notes |
|---|---|
| `bash` | |
| `python3` | Standard library only — the bundled filter needs no extra packages |
| `R` (>= 3.6) with `tidyr`, `vcfR`, `data.table` | Missing packages are installed automatically on first run |

### Genotyping (external, not bundled)

| Tool | Role |
|---|---|
| **HipSTR** | Genotypes the discovered loci from sequencing data. Run by the user between Step 1 and Step 2. See https://github.com/HipSTR-Tool/HipSTR |

Upstream read processing (quality control, alignment, sorting) is performed with standard tools of your choice before HipSTR (e.g. fastp, bwa, samtools). See the accompanying publication for the exact versions used in the reference study.

---

# Building from source

To produce a stand-alone bundle:

```bash
pip install .[package]      # installs PyInstaller
pyinstaller pSTRminer.spec
```

The result is a self-contained directory at `dist/pSTRminer/`, containing the `pSTRminer` executable together with its bundled scripts and libraries. Distribute the directory as a whole — the executable will not run if separated from it.

---

# Citation

If you use pSTRminer in your research, please cite the accompanying publication. Citation details will be added here upon publication.

Please also cite the underlying tools:

- **HipSTR:** Willems T, et al. (2017) *Nature Methods* 14:590–592
- **TRF:** Benson G. (1999) *Nucleic Acids Research* 27:573–580
- **BWA:** Li H & Durbin R. (2009) *Bioinformatics* 25:1754–1760
- **SAMtools:** Danecek P, et al. (2021) *GigaScience* 10:giab008

---

# License

pSTRminer is released under the **MIT License** — see [LICENSE](LICENSE).

Bundled third-party components and their licences are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

# Support

Open a GitHub Issue for bugs or feature requests. Please include the full log output and the command you ran.

---

*pSTRminer  |  HipSTR pipeline  |  For academic & forensic research use*
[github.com/liujj-git/pSTRminer](https://github.com/liujj-git/pSTRminer)
