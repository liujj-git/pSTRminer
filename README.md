#STR Analysis Pipeline for Forensic Genetics
#Overview
#This repository provides a complete, automated pipeline for STR (Short Tandem Repeat) analysis in forensic genetics applications. 
#The pipeline integrates configuration generation, genotype filtering, and forensic parameter calculation into a streamlined workflow that processes HipSTR output through to comprehensive forensic reports.
#Workflow Summary
#HipSTR Configuration → STR Genotyping → VCF Filtering → Genotype Conversion → Forensic Analysis
      (Script 1)         (External)       (Script 2)        (R Script)        (R Script)


Prerequisites and Dependencies
System Tools:
Python 2.7+ (for filter_vcf.py)
R 3.6+ with packages: tidyr, vcfR, data.table
Bioinformatics tools: bgzip, tabix, bedtools, faidx
TRF: Tandem Repeats Finder (automatically downloaded by HipSTR_configuration.sh)
Data Requirements:
Reference genome (FASTA format) or UCSC genome identifier
HipSTR configuration file (BED format, from HipSTR_configuration.sh)
VCF files from HipSTR genotyping (raw or pre-filtered)


Scripts and Their Functions
1. HipSTR_configuration.sh
Generates HipSTR configuration files from reference genomes for STR genotyping.
Key Features:
Downloads reference genomes from UCSC or uses local FASTA files
Runs Tandem Repeats Finder (TRF) to identify STR regions
Filters and formats STR regions for HipSTR analysis
Outputs bed-formatted configuration files with motif information
Output:
{genome}.configuration.bed - Complete STR regions
{genome}.configuration.DitoHex.bed - Filtered (no mononucleotide repeats)

2. Polymorphism.sh (formerly run_STR_filter_convert.sh)
Processes HipSTR VCF outputs through filtering and genotype conversion to forensic parameters.
Two Operation Modes:
Mode T: Filters raw HipSTR VCF and performs genotype conversion
Mode F: Skips filtering for pre-filtered VCFs and performs genotype conversion
Key Features:
Integrates filter_vcf.py from HipSTR-references for quality filtering
Validates parameter combinations to prevent misuse
Provides detailed progress tracking and error reporting
Generates comprehensive analysis reports
Output:
{prefix}.filtered.vcf - Quality-filtered VCF (Mode T only)
{prefix}.allele_sequence.txt - Allele sequences and copy numbers
{prefix}.GT.copynumber.txt - Copy number-based genotypes
{prefix}.forensic_parameters.txt - Forensic genetic parameters
{prefix}.allele_freq.txt - Allele frequencies
{prefix}.analysis_report.txt - Complete analysis summary

3. STR_analysis_pipeline.R
Integrated R script that combines three analysis steps into a single pipeline.
Three Integrated Functions:
Asequence.R: Analyzes allele sequences from VCF files and calculates copy numbers
copynumberGT.R: Converts genotype calls to copy number representation
forensic_parameter.R: Calculates forensic genetic parameters and allele frequencies
Key Features:
Single-command execution for all analysis steps
Handles complex allele structures and multi-allelic sites
Calculates 10+ forensic parameters including Ho, He, DP, PIC, etc.
Generates formatted output files for downstream analysis


Complete Workflow Steps
Step 1: Configuration Generation (User-run)
# Download reference genome
./HipSTR_configuration.sh -R hg38
# Or use local reference
./HipSTR_configuration.sh --reference /path/to/genome.fa

Step 2: STR Genotyping (External/User-run)
# Run HipSTR with generated configuration
hipstr \
  --bams sample_bams.list \
  --fasta reference_genome/hg38.fa \
  --regions reference_genome/hg38.configuration.DitoHex.bed \
  --str-vcf raw_str_calls.vcf.gz

Step 3: Filtering and Analysis (User-run)
# Mode T: Raw VCF needs filtering
./Polymorphism.sh \
  -C reference_genome/hg38.configuration.DitoHex.bed \
  -I raw_str_calls.vcf.gz \
  -O final_results \
  -F T \
  --filter-script HipSTR-references/scripts/filter_vcf.py \
  --min-call-qual 0.9 \
  --max-call-flank-indel 0.15 \
  --max-call-stutter 0.15 \
  --min-call-allele-bias -2 \
  --min-call-strand-bias -2
# Mode F: Already filtered VCF
./Polymorphism.sh \
  -C reference_genome/hg38.configuration.DitoHex.bed \
  -I pre_filtered.vcf \
  -O final_results \
  -F F


User Responsibilities
Required User Actions:
Reference Preparation: Obtain reference genome (FASTA format)
Sample Preparation: Prepare BAM files aligned to reference genome
HipSTR Execution: Run HipSTR genotyping (external to this pipeline)
Output Management: Organize and store analysis results

Optional User Actions:
Parameter Customization: Adjust filtering thresholds as needed
Quality Control: Review intermediate files and logs
Result Interpretation: Analyze forensic parameters for research/forensic applications

Output Interpretation
Key Forensic Parameters:
N: Number of alleles
Na: Number of allele types
Ho: Observed heterozygosity
He: Expected heterozygosity
DP: Discrimination power
PIC: Polymorphism information content
MP: Match probability
PE2/PE3: Paternity exclusion probabilities

Quality Metrics:
Filtering statistics in {prefix}.analysis_report.txt
Allele frequency distributions
Sample and locus counts


Quick Start Guide
1. Clone repository and install dependencies:
git clone https://github.com/yourusername/str-analysis-pipeline.git
cd str-analysis-pipeline
chmod +x HipSTR_configuration.sh Polymorphism.sh STR_analysis_pipeline.R
# Install R packages
Rscript -e "install.packages(c('tidyr', 'vcfR', 'data.table'), repos='https://cloud.r-project.org')"

2. Generate HipSTR configuration:
./HipSTR_configuration.sh -R hg38

3. Run HipSTR (external) to generate VCF files

4. Process VCF files with polymorphism analysis:
./Polymorphism.sh -C config.bed -I input.vcf -O results -F T \
  --filter-script filter_vcf.py --min-call-qual 0.9 \
  --max-call-flank-indel 0.15 --max-call-stutter 0.15 \
  --min-call-allele-bias -2 --min-call-strand-bias -2


Notes and Limitations
Python 2 Requirement: The filter_vcf.py script requires Python 2.7
HipSTR Dependency: This pipeline processes HipSTR output but doesn't include HipSTR itself
Reference Compatibility: Ensure consistency between reference genome used for alignment and configuration generation
Large Datasets: May require significant memory for large sample sizes (>1000 samples)


Citation and Attribution
If you use this pipeline in your research, please cite:
HipSTR: https://github.com/HipSTR-Tool/HipSTR
Tandem Repeats Finder: Benson, G. (1999) Nucleic Acids Research

Support and Contributions
For issues, questions, or contributions：
Open an Issue on GitHub.
Provide example files for troubleshooting.
Include complete command logs and error messages.

License
This pipeline is provided for academic and research use. Please see individual script headers for specific licensing information.
