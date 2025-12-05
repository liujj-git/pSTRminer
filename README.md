# STR Analysis Pipeline for Forensic Genetics

## Overview
This repository provides a complete, automated pipeline for STR (Short Tandem Repeat) analysis in forensic genetics applications. The pipeline integrates STR mining, variant calling, and polymorphism evaluation into a streamlined workflow that processes HipSTR output through to comprehensive forensic reports.

## Workflow Summary
```
HipSTR Configuration → STR Genotyping → VCF Filtering → Genotype Conversion → Forensic Analysis
      (Script 1)         (External)       (Script 2)        (R Script)        (R Script)
```

## Scripts and Their Functions

### 1. **HipSTR_configuration.sh**
Generates HipSTR configuration files from reference genomes for STR genotyping.

**Key Features:**
- Downloads reference genomes from UCSC or uses local FASTA files
- Runs Tandem Repeats Finder (TRF) to identify STR regions
- Filters and formats STR regions for HipSTR analysis
- Outputs bed-formatted configuration files with motif information

**Usage:**
```bash
# Download UCSC reference genome
./HipSTR_configuration.sh -R mm10

# Or use local reference
./HipSTR_configuration.sh --reference /path/to/genome.fa
```

**Output:**
- `reference_genome/{genome}.configuration.bed` - Complete STR regions
- `reference_genome/{genome}.configuration.DitoHex.bed` - Filtered (no mononucleotide repeats)

### 2. **Polymorphism.sh**
Processes HipSTR VCF outputs through filtering and genotype conversion to forensic parameters.

**Two Operation Modes:**
- **Mode T**: Filters raw HipSTR VCF and performs genotype conversion
- **Mode F**: Skips filtering for pre-filtered VCFs and performs genotype conversion

**Required Parameters (All Modes):**
- `-C <config.bed>`: HipSTR configuration file
- `-I <input.vcf>`: Input VCF file from HipSTR
- `-O <output_prefix>`: Prefix for all output files
- `-F <T/F>`: Specify whether filtering is required

**Additional Required Parameters (Mode T only):**
- `--filter-script <path>`: Path to `filter_vcf.py` script
- `--min-call-qual <value>`: Minimum call quality (default: 0.9)
- `--max-call-flank-indel <value>`: Maximum flanking indel frequency (default: 0.15)
- `--max-call-stutter <value>`: Maximum stutter frequency (default: 0.15)
- `--min-call-allele-bias <value>`: Minimum allele bias (default: -2)
- `--min-call-strand-bias <value>`: Minimum strand bias (default: -2)

**Usage Examples:**
```bash
# Mode T: Filter and analyze a raw VCF
./Polymorphism.sh -C hg38.configuration.DitoHex.bed \
                  -I hipstr_raw.vcf.gz \
                  -O my_study \
                  -F T \
                  --filter-script HipSTR-references/scripts/filter_vcf.py \
                  --min-call-qual 0.9 \
                  --max-call-flank-indel 0.15 \
                  --max-call-stutter 0.15 \
                  --min-call-allele-bias -2 \
                  --min-call-strand-bias -2

# Mode F: Analyze a pre-filtered VCF
./Polymorphism.sh -C hg38.configuration.DitoHex.bed \
                  -I pre_filtered.vcf \
                  -O my_study \
                  -F F
```

**Output:**
- `{prefix}.filtered.vcf` - Quality-filtered VCF (Mode T only)
- `{prefix}.allele_sequence.txt` - Allele sequences and copy numbers
- `{prefix}.GT.copynumber.txt` - Copy number-based genotypes
- `{prefix}.forensic_parameters.txt` - Forensic genetic parameters
- `{prefix}.allele_freq.txt` - Allele frequencies
- `{prefix}.analysis_report.txt` - Complete analysis summary

### 3. **STR_analysis_pipeline.R**
Integrated R script that combines three analysis steps into a single pipeline.

**Three Integrated Functions:**
1. **Asequence.R**: Analyzes allele sequences from VCF files and calculates copy numbers
2. **copynumberGT.R**: Converts genotype calls to copy number representation
3. **forensic_parameter.R**: Calculates forensic genetic parameters and allele frequencies

**Key Features:**
- Single-command execution for all analysis steps
- Handles complex allele structures and multi-allelic sites
- Calculates forensic parameters including Ho, He, DP, PIC, etc.
- Generates formatted output files for downstream analysis

**Dependencies:**
- R packages: `tidyr`, `vcfR`, `data.table`

## Prerequisites and Dependencies

### System Tools:
- **Python 2.7+** (for filter_vcf.py)
- **R 3.6+** with packages: `tidyr`, `vcfR`, `data.table`
- **Bioinformatics tools**: `bgzip`, `tabix`, `bedtools`, `faidx`, `wget`, `git`
- **TRF**: Tandem Repeats Finder (automatically downloaded by HipSTR_configuration.sh)

### Data Requirements:
- Reference genome (FASTA format) or UCSC genome identifier
- HipSTR configuration file (BED format, from HipSTR_configuration.sh)
- VCF files from HipSTR genotyping (raw or pre-filtered)

## Complete Workflow Example

```bash
# Step 1: Generate HipSTR configuration for human genome
./HipSTR_configuration.sh -R hg38

# Step 2: Run HipSTR genotyping on your BAM files (EXTERNAL STEP)
# hipstr --bams bam_list.txt --fasta hg38.fa \
#        --regions reference_genome/hg38.configuration.DitoHex.bed \
#        --str-vcf my_data.vcf.gz

# Step 3: Filter raw HipSTR VCF and perform forensic analysis
./Polymorphism.sh -C reference_genome/hg38.configuration.DitoHex.bed \
                  -I my_data.vcf.gz \
                  -O forensic_results \
                  -F T \
                  --filter-script HipSTR-references/scripts/filter_vcf.py \
                  --min-call-qual 0.9 \
                  --max-call-flank-indel 0.15 \
                  --max-call-stutter 0.15 \
                  --min-call-allele-bias -2 \
                  --min-call-strand-bias -2
```

## Output Interpretation

### Key Forensic Parameters:
- **N**: Number of alleles
- **Na**: Number of allele types
- **Ho**: Observed heterozygosity
- **He**: Expected heterozygosity  
- **DP**: Discrimination power
- **PIC**: Polymorphism information content
- **MP**: Match probability
- **PE2/PE3**: Paternity exclusion probabilities


## Quick Start Guide

1. Clone repository and install dependencies:
```bash
git clone https://github.com/yourusername/pSTR_finder.git
cd pSTR_finder
chmod +x HipSTR_configuration.sh Polymorphism.sh STR_analysis_pipeline.R

# Install R packages
Rscript -e "install.packages(c('tidyr', 'vcfR', 'data.table'), repos='https://cloud.r-project.org')"
```

2. Generate HipSTR configuration:
```bash
./HipSTR_configuration.sh -R mm10
```

3. Run HipSTR (external) to generate VCF files

4. Process VCF files with polymorphism analysis:
```bash
./Polymorphism.sh -C config.bed -I input.vcf -O results -F T \
  --filter-script filter_vcf.py --min-call-qual 0.9 \
  --max-call-flank-indel 0.15 --max-call-stutter 0.15 \
  --min-call-allele-bias -2 --min-call-strand-bias -2
```

## User Responsibilities

### Required User Actions:
1. **Reference Preparation**: Obtain reference genome (FASTA format)
2. **Sample Preparation**: Prepare BAM files aligned to reference genome
3. **HipSTR Execution**: Run HipSTR genotyping (external to this pipeline)
4. **Output Management**: Organize and store analysis results

### Optional User Actions:
1. **Parameter Customization**: Adjust filtering thresholds as needed
2. **Quality Control**: Review intermediate files and logs
3. **Result Interpretation**: Analyze forensic parameters for research/forensic applications

## Notes and Limitations

- **Python 2 Requirement**: The `filter_vcf.py` script requires Python 2.7
- **HipSTR Dependency**: This pipeline processes HipSTR output but doesn't include HipSTR itself
- **Reference Compatibility**: Ensure consistency between reference genome used for alignment and configuration generation
- **Large Datasets**: May require significant memory for large sample sizes

## Citation and Attribution

If you use this pipeline in your research, please cite:
- HipSTR: https://github.com/HipSTR-Tool/HipSTR
- Tandem Repeats Finder: Benson, G. (1999) Nucleic Acids Research

## Support and Contributions

For issues, questions, or contributions:
- Open an Issue on GitHub
- Provide example files for troubleshooting
- Include complete command logs and error messages

## License

This pipeline is provided for academic and research use. 

---
