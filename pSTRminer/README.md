# pSTRminer

**Integrated STR Analysis Pipeline for Forensic Genetics**

pSTRminer provides a complete, reproducible workflow for genome-wide discovery and population-scale evaluation of polymorphic short tandem repeats (STRs). It is available as both a **graphical desktop application** (Windows / macOS / Linux) and a **command-line tool**.

---

## Features

| Feature | Description |
|---|---|
| **STR Mining** | Identifies genome-wide STRs via Tandem Repeats Finder (TRF) and generates HipSTR configuration files |
| **Polymorphism Evaluation** | Filters HipSTR VCF output and calculates 10 forensic-genetic parameters (PIC, Ho, He, DP, MP, PE, Ae, …) |
| **Graphical Interface** | Tkinter-based GUI — no command-line experience required |
| **Command-Line Interface** | Full CLI for server/HPC environments and scripted pipelines |
| **Cross-platform** | Runs on Linux, macOS and Windows |
| **Self-contained** | All HipSTR auxiliary scripts are bundled — no separate downloads needed |

---

## Quick Start

### 1 – Download

Download the latest release for your platform from the [Releases](../../releases) page and unzip.

| Platform | Executable |
|---|---|
| Linux   | `pSTRminer` (chmod +x first) |
| macOS   | `pSTRminer.app` or `pSTRminer` binary |
| Windows | `pSTRminer.exe` |

### 2 – Launch GUI

Double-click the executable (or run `./pSTRminer` on Linux/macOS) with no arguments to open the graphical interface.

### 3 – Use CLI

```bash
# Show help
./pSTRminer --help
./pSTRminer config --help
./pSTRminer poly   --help
```

---

## Workflow Overview

```
Reference genome
      │
      ▼
┌─────────────────────────────┐
│  Step 1: STR Configuration  │  HipSTR_configuration.sh
│  • TRF-based STR mining     │  → *.configuration.DitoHex.bed
│  • HipSTR config generation │
└─────────────────────────────┘
              │
              │  (User runs HipSTR externally)
              │  hipstr --bams bam_list.txt --fasta genome.fa \
              │          --regions config.DitoHex.bed \
              │          --str-vcf output.vcf.gz
              ▼
┌──────────────────────────────────┐
│  Step 2: Polymorphism Analysis   │  Polymorphism.sh
│  • VCF quality filtering         │  → *.forensic_parameters.txt
│  • Allele calling & conversion   │  → *.allele_freq.txt
│  • Forensic parameter calculation│  → *.GT.copynumber.txt
└──────────────────────────────────┘
```

> **Note:** HipSTR itself is not bundled. Install it from https://github.com/HipSTR-Tool/HipSTR.

---

## GUI Usage

### Step 1 – STR Configuration

1. Open the **Step 1 – STR Configuration** tab.
2. Choose a reference source:
   - **Download from UCSC** – enter a genome identifier (e.g. `bosTau9`, `hg38`, `mm10`).
   - **Use local FASTA file** – browse to a `.fa` / `.fasta` file.
3. Set the output directory.
4. Click **▶ Run Configuration**.
5. Monitor progress in the log console on the right.

### Step 2 – Polymorphism Analysis

1. Open the **Step 2 – Polymorphism Analysis** tab.
2. Select the HipSTR config BED file generated in Step 1.
3. Select the HipSTR output VCF file.
4. Set the output directory and file prefix.
5. Choose filtering mode:
   - **Mode T** (default) – filter raw HipSTR VCF using the quality thresholds shown.
   - **Mode F** – skip filtering (VCF is already filtered).
6. Click **▶ Run Analysis**.

---

## CLI Usage

### Step 1 – STR Configuration

```bash
# Download bosTau9 from UCSC and generate configuration
./pSTRminer config -o ./results -R bosTau9

# Use a local reference FASTA
./pSTRminer config -o ./results --reference /data/bosTau9.fa
```

**Output files** (in `./results/reference_genome/`):
- `bosTau9.configuration.bed` – all STR regions
- `bosTau9.configuration.DitoHex.bed` – filtered (dinucleotide to hexanucleotide only)

### Step 2 – Polymorphism Analysis

```bash
# Mode T: Filter raw HipSTR VCF and calculate parameters
./pSTRminer poly \
  -o ./results \
  -C results/reference_genome/bosTau9.configuration.DitoHex.bed \
  -I hipstr_output.vcf.gz \
  -O my_study \
  -F T \
  --min-call-qual 0.9 \
  --max-call-flank-indel 0.15 \
  --max-call-stutter 0.15 \
  --min-call-allele-bias -2 \
  --min-call-strand-bias -2

# Mode F: Skip filtering (pre-filtered VCF)
./pSTRminer poly \
  -o ./results \
  -C config.bed \
  -I pre_filtered.vcf \
  -O my_study \
  -F F
```

**Output files** (in `./results/`):
| File | Description |
|---|---|
| `my_study.filtered.vcf` | Quality-filtered VCF (Mode T only) |
| `my_study.allele_sequence.txt` | Allele sequences and copy numbers |
| `my_study.GT.copynumber.txt` | Copy-number genotype matrix |
| `my_study.forensic_parameters.txt` | All forensic parameters per locus |
| `my_study.allele_freq.txt` | Allele frequencies per locus |
| `my_study.analysis_report.txt` | Summary statistics |

---

## Forensic Parameters Calculated

| Parameter | Symbol | Description |
|---|---|---|
| Number of alleles | N | Total allele count across samples |
| Allele types | Na | Number of distinct alleles |
| Observed heterozygosity | Ho | Proportion of heterozygous genotypes |
| Expected heterozygosity | He | Hardy–Weinberg expected heterozygosity |
| Match probability | MP | Probability of a random match |
| Discrimination power | PD | 1 – MP (power to discriminate) |
| Exclusion probability (duo) | PE₂ | Parentage exclusion for duos |
| Exclusion probability (trio) | PE₃ | Parentage exclusion for trios |
| Polymorphism information content | PIC | Informativeness for marker selection |
| Effective allele number | Ae | Effective number of alleles |

---

## Filtering Parameters (Mode T)

| Parameter | Default | Description |
|---|---|---|
| Minimum call quality | 0.9 | Per-genotype quality score threshold |
| Max flanking indel rate | 0.15 | Maximum allowed flanking indel frequency |
| Max stutter rate | 0.15 | Maximum allowed stutter frequency |
| Min allele bias | –2 | Minimum allele balance log-ratio |
| Min strand bias | –2 | Minimum strand balance log-ratio |

---

## Prerequisites

### Required for runtime:
- **Python 3.7+** (if running from source)
- **Bash** (Linux / macOS) — the pipeline scripts are bash-based
- **Python 2.7** — required by `filter_vcf.py` (HipSTR's filtering script)
- **Bioinformatics tools:** `bedtools`, `samtools faidx` (`faidx`), `bgzip`, `tabix`, `wget`, `git`
- **R 3.6+** with packages: `tidyr`, `vcfR`, `data.table`

### Required for Step 1 (auto-downloaded):
- **TRF** (Tandem Repeats Finder) — downloaded automatically on first run

### Required for genotyping (external — not bundled):
- **HipSTR** — https://github.com/HipSTR-Tool/HipSTR

---

## Installation from Source

```bash
git clone https://github.com/Sunlab-forensicsysu/pSTRminer.git
cd pSTRminer

# Install Python package (optional, for CLI entry point)
pip install -e .

# Launch GUI
python -m pstrminer

# Or use CLI
python -m pstrminer config -o ./out -R bosTau9
python -m pstrminer poly   -o ./out -C config.bed -I data.vcf -O results -F T ...
```

---

## Building Standalone Executables

```bash
pip install pyinstaller
cd pSTRminer
pyinstaller pSTRminer.spec
# Output: dist/pSTRminer/pSTRminer (or .exe on Windows)
```

---

## Citation

If you use pSTRminer in your research, please cite:

> [manuscript citation — to be updated upon publication]

Please also cite the underlying tools:
- **HipSTR:** Willems T, et al. (2017) *Nature Methods* 14:590–592
- **TRF:** Benson G. (1999) *Nucleic Acids Research* 27:573–580
- **BWA:** Li H & Durbin R. (2009) *Bioinformatics* 25:1754–1760
- **SAMtools:** Danecek P, et al. (2021) *GigaScience* 10:giab008

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Support

- Open a GitHub Issue for bugs or feature requests
- Include the full log output and your command when reporting issues
