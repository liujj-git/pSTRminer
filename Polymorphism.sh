#!/bin/bash
# STR Genotype Filtering and Conversion Pipeline
# Integration of filter_vcf.py filtering and R script genotype conversion
# Usage: ./run_STR_filter_convert.sh -C <config_file> -I <input_VCF> -O <output_prefix> -F <T/F>

# Color settings
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored messages
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_debug() {
    echo -e "${CYAN}[DEBUG]${NC} $1"
}

# Default parameters
CONFIG_FILE=""
INPUT_VCF=""
OUTPUT_PREFIX=""
FILTER_SCRIPT=""
NEEDS_FILTER=""  # Must be specified, no default
MIN_CALL_QUAL=""
MAX_CALL_FLANK_INDEL=""
MAX_CALL_STUTTER=""
MIN_CALL_ALLELE_BIAS=""
MIN_CALL_STRAND_BIAS=""

# Function: Display usage
usage() {
    echo "=================================================="
    echo "STR Genotype Filtering and Conversion Pipeline"
    echo "=================================================="
    echo "Usage: $0 -C <config_file> -I <input_VCF> -O <output_prefix> -F <T/F>"
    echo ""
    echo "Required parameters:"
    echo "  -C <file>      : HipSTR configuration file (bed format)"
    echo "  -I <file>      : Input VCF file"
    echo "  -O <prefix>    : Output file prefix"
    echo "  -F <T/F>       : Whether filtering is needed (T=needs filtering, F=already filtered)"
    echo ""
    echo "When -F T (needs filtering):"
    echo "  The following parameters must all be specified:"
    echo "  --filter-script <path>   : Path to filter_vcf.py script"
    echo "  --min-call-qual <value>  : Minimum call quality"
    echo "  --max-call-flank-indel <value> : Maximum flank indel frequency"
    echo "  --max-call-stutter <value> : Maximum stutter frequency"
    echo "  --min-call-allele-bias <value> : Minimum allele bias"
    echo "  --min-call-strand-bias <value> : Minimum strand bias"
    echo ""
    echo "When -F F (already filtered):"
    echo "  Skip filtering step, proceed directly to genotype conversion"
    echo "  No filtering parameters can be specified"
    echo ""
    echo "Examples:"
    echo "  Case 1: Needs filtering:"
    echo "    $0 -C config.bed -I raw.vcf -O filtered -F T \\"
    echo "       --filter-script /path/to/filter_vcf.py \\"
    echo "       --min-call-qual 0.9 \\"
    echo "       --max-call-flank-indel 0.15 \\"
    echo "       --max-call-stutter 0.15 \\"
    echo "       --min-call-allele-bias -2 \\"
    echo "       --min-call-strand-bias -2"
    echo ""
    echo "  Case 2: Already filtered:"
    echo "    $0 -C config.bed -I filtered.vcf -O final -F F"
    echo ""
    echo "General options:"
    echo "  -h, --help     : Display this help message"
    echo "=================================================="
    exit 1
}

# Function: Check if all required parameters are provided
check_required_params() {
    local missing=()
    
    # Check general required parameters
    if [[ -z "$CONFIG_FILE" ]]; then
        missing+=("-C (config file)")
    fi
    
    if [[ -z "$INPUT_VCF" ]]; then
        missing+=("-I (input VCF)")
    fi
    
    if [[ -z "$OUTPUT_PREFIX" ]]; then
        missing+=("-O (output prefix)")
    fi
    
    if [[ -z "$NEEDS_FILTER" ]]; then
        missing+=("-F (filter flag)")
    fi
    
    # Check required parameters when -F T
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        if [[ -z "$FILTER_SCRIPT" ]]; then
            missing+=("--filter-script (filter script)")
        fi
        if [[ -z "$MIN_CALL_QUAL" ]]; then
            missing+=("--min-call-qual (minimum call quality)")
        fi
        if [[ -z "$MAX_CALL_FLANK_INDEL" ]]; then
            missing+=("--max-call-flank-indel (maximum flank indel frequency)")
        fi
        if [[ -z "$MAX_CALL_STUTTER" ]]; then
            missing+=("--max-call-stutter (maximum stutter frequency)")
        fi
        if [[ -z "$MIN_CALL_ALLELE_BIAS" ]]; then
            missing+=("--min-call-allele-bias (minimum allele bias)")
        fi
        if [[ -z "$MIN_CALL_STRAND_BIAS" ]]; then
            missing+=("--min-call-strand-bias (minimum strand bias)")
        fi
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required parameters:"
        for param in "${missing[@]}"; do
            echo "  $param"
        done
        echo ""
        echo "Please see usage:"
        usage
    fi
}

# Function: Check parameter compatibility
check_parameter_compatibility() {
    print_debug "Checking parameter compatibility"
    
    # Check if filtering parameters are specified when -F F
    if [[ "$NEEDS_FILTER" == "F" ]]; then
        local filter_params=()
        [[ -n "$FILTER_SCRIPT" ]] && filter_params+=("--filter-script")
        [[ -n "$MIN_CALL_QUAL" ]] && filter_params+=("--min-call-qual")
        [[ -n "$MAX_CALL_FLANK_INDEL" ]] && filter_params+=("--max-call-flank-indel")
        [[ -n "$MAX_CALL_STUTTER" ]] && filter_params+=("--max-call-stutter")
        [[ -n "$MIN_CALL_ALLELE_BIAS" ]] && filter_params+=("--min-call-allele-bias")
        [[ -n "$MIN_CALL_STRAND_BIAS" ]] && filter_params+=("--min-call-strand-bias")
        
        if [[ ${#filter_params[@]} -gt 0 ]]; then
            print_error "Error: When -F F, no filtering parameters can be specified"
            echo ""
            echo "Filtering parameters specified: ${filter_params[*]}"
            echo "Reason: -F F indicates input VCF is already filtered, no filtering parameters allowed"
            echo ""
            echo "Correct usage:"
            echo "  $0 -C config.bed -I filtered.vcf -O final -F F"
            exit 1
        fi
    fi
    
    # Check if filter script exists when -F T
    if [[ "$NEEDS_FILTER" == "T" ]] && [[ ! -f "$FILTER_SCRIPT" ]]; then
        print_error "filter_vcf.py script not found: $FILTER_SCRIPT"
        print_info "Please ensure the specified path is correct, or that HipSTR-references directory exists"
        exit 1
    fi
}

# Function: Parse command line arguments
parse_arguments() {
    print_step "Parsing command line arguments"
    
    # Check if any arguments are provided
    if [ $# -eq 0 ]; then
        print_error "No arguments provided"
        usage
    fi
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -C|--config)
                CONFIG_FILE="$2"
                if [[ ! -f "$CONFIG_FILE" ]]; then
                    print_error "Config file not found: $CONFIG_FILE"
                    exit 1
                fi
                print_info "Config file: $CONFIG_FILE"
                shift 2
                ;;
            -I|--input)
                INPUT_VCF="$2"
                if [[ ! -f "$INPUT_VCF" ]]; then
                    print_error "Input VCF file not found: $INPUT_VCF"
                    exit 1
                fi
                print_info "Input VCF: $INPUT_VCF"
                shift 2
                ;;
            -O|--output)
                OUTPUT_PREFIX="$2"
                print_info "Output prefix: $OUTPUT_PREFIX"
                shift 2
                ;;
            -F)
                NEEDS_FILTER="$2"
                if [[ ! "$NEEDS_FILTER" =~ ^[TFtf]$ ]]; then
                    print_error "Invalid -F parameter: $2 (must be T or F)"
                    exit 1
                fi
                # Convert to uppercase
                NEEDS_FILTER=$(echo "$NEEDS_FILTER" | tr '[:lower:]' '[:upper:]')
                print_info "Filter flag: $NEEDS_FILTER"
                shift 2
                ;;
            --filter-script)
                FILTER_SCRIPT="$2"
                print_info "Filter script: $FILTER_SCRIPT"
                shift 2
                ;;
            --min-call-qual)
                MIN_CALL_QUAL="$2"
                print_info "Minimum call quality: $MIN_CALL_QUAL"
                shift 2
                ;;
            --max-call-flank-indel)
                MAX_CALL_FLANK_INDEL="$2"
                print_info "Maximum flank indel frequency: $MAX_CALL_FLANK_INDEL"
                shift 2
                ;;
            --max-call-stutter)
                MAX_CALL_STUTTER="$2"
                print_info "Maximum stutter frequency: $MAX_CALL_STUTTER"
                shift 2
                ;;
            --min-call-allele-bias)
                MIN_CALL_ALLELE_BIAS="$2"
                print_info "Minimum allele bias: $MIN_CALL_ALLELE_BIAS"
                shift 2
                ;;
            --min-call-strand-bias)
                MIN_CALL_STRAND_BIAS="$2"
                print_info "Minimum strand bias: $MIN_CALL_STRAND_BIAS"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                print_error "Unknown parameter: $1"
                usage
                ;;
        esac
    done
    
    # Check if all required parameters are provided
    check_required_params
    
    # Check parameter compatibility
    check_parameter_compatibility
    
    print_info "All parameters validated successfully"
}

# Function: Check dependencies
check_dependencies() {
    print_step "Checking system dependencies"
    
    local deps=("python" "Rscript")
    
    # Add dependencies based on filtering needs
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        deps+=("bgzip" "tabix")
    fi
    
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            missing+=("$dep")
            print_error "Missing dependency: $dep"
        else
            print_info "Found: $dep ($($dep --version 2>/dev/null | head -1 || echo "version unknown"))"
        fi
    done
    
    if [[ ${#missing[@]} -ne 0 ]]; then
        print_error "Missing required dependencies: ${missing[*]}"
        print_info "Please install missing dependencies before running"
        exit 1
    fi
    
    # Check R packages
    print_step "Checking R package dependencies"
    R_CHECK_SCRIPT="
    packages <- c('tidyr', 'vcfR', 'data.table')
    missing_packages <- packages[!packages %in% installed.packages()[,'Package']]
    
    if (length(missing_packages) > 0) {
        cat('Missing R packages:', paste(missing_packages, collapse=', '), '\n')
        cat('Installing...\n')
        install.packages(missing_packages, repos='https://cloud.r-project.org')
    }
    cat('All R packages installed\n')
    "
    
    if Rscript -e "$R_CHECK_SCRIPT" 2>/dev/null; then
        print_info "R package check completed"
    else
        print_error "R package check failed"
        exit 1
    fi
    
    print_info "All dependency checks passed"
}

# Function: Preprocess VCF file
preprocess_vcf() {
    print_step "Preprocessing VCF file"
    
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        # Need filtering: check if input VCF needs compression and indexing
        if [[ "$INPUT_VCF" == *.gz ]]; then
            print_info "Input VCF is already compressed, using existing file"
            VCF_GZ="$INPUT_VCF"
            
            # Check if index file exists
            if [[ ! -f "${INPUT_VCF}.tbi" ]]; then
                print_warning "VCF index file not found, creating..."
                tabix -p vcf "$INPUT_VCF"
            fi
        else
            print_info "Compressing VCF file..."
            bgzip -c "$INPUT_VCF" > "${OUTPUT_PREFIX}.input.vcf.gz"
            VCF_GZ="${OUTPUT_PREFIX}.input.vcf.gz"
            
            print_info "Creating VCF index..."
            tabix -p vcf "$VCF_GZ"
        fi
        print_info "Preprocessing completed: $VCF_GZ"
    else
        # No filtering needed
        print_info "Input VCF already filtered, skipping preprocessing"
        # Use input VCF directly
        VCF_GZ="$INPUT_VCF"
    fi
}

# Function: Filter VCF
filter_vcf() {
    print_step "Filtering VCF file"
    
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        # Check if filter script exists
        if [[ ! -f "$FILTER_SCRIPT" ]]; then
            print_error "filter_vcf.py script not found: $FILTER_SCRIPT"
            exit 1
        fi
        
        # Set output file path
        FILTERED_VCF="${OUTPUT_PREFIX}.filtered.vcf"
        
        print_info "Starting VCF filtering..."
        print_info "Using parameters:"
        print_info "  --min-call-qual: $MIN_CALL_QUAL"
        print_info "  --max-call-flank-indel: $MAX_CALL_FLANK_INDEL"
        print_info "  --max-call-stutter: $MAX_CALL_STUTTER"
        print_info "  --min-call-allele-bias: $MIN_CALL_ALLELE_BIAS"
        print_info "  --min-call-strand-bias: $MIN_CALL_STRAND_BIAS"
        
        # Execute filtering
        python "$FILTER_SCRIPT" \
            --vcf "$VCF_GZ" \
            --min-call-qual "$MIN_CALL_QUAL" \
            --max-call-flank-indel "$MAX_CALL_FLANK_INDEL" \
            --max-call-stutter "$MAX_CALL_STUTTER" \
            --min-call-allele-bias "$MIN_CALL_ALLELE_BIAS" \
            --min-call-strand-bias "$MIN_CALL_STRAND_BIAS" > "$FILTERED_VCF"
        
        # Check if filtering was successful
        if [[ $? -eq 0 ]] && [[ -f "$FILTERED_VCF" ]] && [[ $(wc -l < "$FILTERED_VCF" 2>/dev/null || echo 0) -gt 10 ]]; then
            FILTERED_COUNT=$(grep -c -v "^#" "$FILTERED_VCF")
            print_info "Filtering completed: $FILTERED_VCF"
            print_info "Number of filtered loci: $FILTERED_COUNT"
        else
            print_error "VCF filtering failed"
            exit 1
        fi
    else
        print_info "Input VCF already filtered, skipping filtering step"
        # No filtering needed, use original file
        FILTERED_VCF="$INPUT_VCF"
        print_info "Using already filtered VCF file: $FILTERED_VCF"
    fi
}

# Function: Run genotype conversion R script
run_genotype_conversion() {
    print_step "Running genotype conversion"
    
    # Determine which VCF file to use
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        VCF_TO_CONVERT="${OUTPUT_PREFIX}.filtered.vcf"
    else
        VCF_TO_CONVERT="$INPUT_VCF"
    fi
    
    # Check if VCF exists
    if [[ ! -f "$VCF_TO_CONVERT" ]]; then
        print_error "VCF file not found: $VCF_TO_CONVERT"
        exit 1
    fi
    
    # Check if R script exists
    if [[ ! -f "STR_analysis_pipeline.R" ]]; then
        print_error "R script not found: STR_analysis_pipeline.R"
        print_info "Please ensure STR_analysis_pipeline.R is in the current directory"
        exit 1
    fi
    
    print_info "Running genotype conversion R script..."
    print_info "Input VCF: $VCF_TO_CONVERT"
    print_info "Config file: $CONFIG_FILE"
    
    # Execute R script
    Rscript STR_analysis_pipeline.R "$VCF_TO_CONVERT" "$CONFIG_FILE"
    
    if [[ $? -eq 0 ]]; then
        print_info "Genotype conversion completed"
        
        # Rename output files to match output prefix
        rename_output_files
    else
        print_error "Genotype conversion failed"
        exit 1
    fi
}

# Function: Rename output files
rename_output_files() {
    print_step "Renaming output files"
    
    # Standard output file list
    standard_files=(
        "allele_sequence.txt"
        "GT.copynumber.txt"
        "forensic_parameters.txt"
        "allele_freq.txt"
        "analysis_summary.txt"
    )
    
    for file in "${standard_files[@]}"; do
        if [[ -f "$file" ]]; then
            new_name="${OUTPUT_PREFIX}.${file}"
            mv "$file" "$new_name"
            print_info "Renamed: $file -> $new_name"
        else
            print_warning "Output file not found: $file"
        fi
    done
}

# Function: Generate analysis report
generate_report() {
    print_step "Generating analysis report"
    
    REPORT_FILE="${OUTPUT_PREFIX}.analysis_report.txt"
    
    echo "==================================================" > "$REPORT_FILE"
    echo "STR Genotype Filtering and Conversion Analysis Report" >> "$REPORT_FILE"
    echo "Generated at: $(date)" >> "$REPORT_FILE"
    echo "==================================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "Input files:" >> "$REPORT_FILE"
    echo "  Config file: $CONFIG_FILE" >> "$REPORT_FILE"
    echo "  Input VCF: $INPUT_VCF" >> "$REPORT_FILE"
    echo "  Filter flag: $NEEDS_FILTER" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        echo "Filtering parameters:" >> "$REPORT_FILE"
        echo "  Minimum call quality: $MIN_CALL_QUAL" >> "$REPORT_FILE"
        echo "  Maximum flank indel frequency: $MAX_CALL_FLANK_INDEL" >> "$REPORT_FILE"
        echo "  Maximum stutter frequency: $MAX_CALL_STUTTER" >> "$REPORT_FILE"
        echo "  Minimum allele bias: $MIN_CALL_ALLELE_BIAS" >> "$REPORT_FILE"
        echo "  Minimum strand bias: $MIN_CALL_STRAND_BIAS" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        
        # Count filtered loci
        if [[ -f "${OUTPUT_PREFIX}.filtered.vcf" ]]; then
            FILTERED_LOCI=$(grep -c "^[^#]" "${OUTPUT_PREFIX}.filtered.vcf" 2>/dev/null || echo "N/A")
            echo "Filtering results:" >> "$REPORT_FILE"
            echo "  Number of filtered loci: $FILTERED_LOCI" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
    else
        echo "Filtering status: Input VCF already filtered, filtering step skipped" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
    
    # Count genotype conversion results
    if [[ -f "${OUTPUT_PREFIX}.forensic_parameters.txt" ]]; then
        LOCI_COUNT=$(tail -n +2 "${OUTPUT_PREFIX}.forensic_parameters.txt" | wc -l)
        SAMPLE_COUNT=$(head -1 "${OUTPUT_PREFIX}.GT.copynumber.txt" | awk '{print NF-1}')
        
        echo "Genotype conversion results:" >> "$REPORT_FILE"
        echo "  Number of analyzed loci: $LOCI_COUNT" >> "$REPORT_FILE"
        echo "  Number of samples: $SAMPLE_COUNT" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        
        # Calculate average heterozygosity
        if [[ $LOCI_COUNT -gt 0 ]]; then
            AVG_HO=$(tail -n +2 "${OUTPUT_PREFIX}.forensic_parameters.txt" | awk -F'\t' '{if($4!="") sum+=$4; count++} END {if(count>0) printf "%.4f", sum/count; else print "N/A"}')
            AVG_HE=$(tail -n +2 "${OUTPUT_PREFIX}.forensic_parameters.txt" | awk -F'\t' '{if($5!="") sum+=$5; count++} END {if(count>0) printf "%.4f", sum/count; else print "N/A"}')
            
            echo "Genetic diversity statistics:" >> "$REPORT_FILE"
            echo "  Average observed heterozygosity (Ho): $AVG_HO" >> "$REPORT_FILE"
            echo "  Average expected heterozygosity (He): $AVG_HE" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
    fi
    
    echo "Output files:" >> "$REPORT_FILE"
    for file in "${OUTPUT_PREFIX}".*; do
        if [[ -f "$file" ]]; then
            size=$(du -h "$file" | cut -f1)
            echo "  - $file ($size)" >> "$REPORT_FILE"
        fi
    done
    
    echo "" >> "$REPORT_FILE"
    echo "Analysis pipeline completed!" >> "$REPORT_FILE"
    echo "==================================================" >> "$REPORT_FILE"
    
    cat "$REPORT_FILE"
    print_info "Detailed report saved to: $REPORT_FILE"
}

# Function: Clean up temporary files
cleanup_temp_files() {
    print_step "Cleaning up temporary files"
    
    # Only clean up compressed files when filtering is needed
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        # Temporary file list
        temp_files=(
            "${OUTPUT_PREFIX}.input.vcf.gz"
            "${OUTPUT_PREFIX}.input.vcf.gz.tbi"
        )
        
        for file in "${temp_files[@]}"; do
            if [[ -f "$file" ]]; then
                rm -f "$file"
                print_info "Deleted temporary file: $file"
            fi
        done
    else
        print_info "No temporary files to clean up (input VCF already filtered)"
    fi
}

# Function: Display workflow summary
show_workflow_summary() {
    print_step "Workflow Summary"
    
    echo "=================================================="
    echo "STR Genotype Filtering and Conversion Pipeline"
    echo "Started at: $(date)"
    echo "=================================================="
    echo ""
    
    print_info "Input parameters:"
    print_info "  Config file: $CONFIG_FILE"
    print_info "  Input VCF: $INPUT_VCF"
    print_info "  Output prefix: $OUTPUT_PREFIX"
    print_info "  Filter flag: $NEEDS_FILTER"
    
    if [[ "$NEEDS_FILTER" == "T" ]]; then
        echo ""
        print_info "Filtering parameters:"
        print_info "  Filter script: $FILTER_SCRIPT"
        print_info "  Minimum call quality: $MIN_CALL_QUAL"
        print_info "  Maximum flank indel frequency: $MAX_CALL_FLANK_INDEL"
        print_info "  Maximum stutter frequency: $MAX_CALL_STUTTER"
        print_info "  Minimum allele bias: $MIN_CALL_ALLELE_BIAS"
        print_info "  Minimum strand bias: $MIN_CALL_STRAND_BIAS"
        echo ""
        print_info "Execution steps:"
        print_info "  1. Check dependencies"
        print_info "  2. Preprocess VCF file (compress/index)"
        print_info "  3. Filter with filter_vcf.py"
        print_info "  4. Run genotype conversion R script"
        print_info "  5. Rename output files"
        print_info "  6. Generate analysis report"
        print_info "  7. Clean up temporary files"
    else
        echo ""
        print_info "Execution steps:"
        print_info "  1. Check dependencies (skip bgzip/tabix)"
        print_info "  2. Skip preprocessing"
        print_info "  3. Skip filtering (input already filtered)"
        print_info "  4. Run genotype conversion R script"
        print_info "  5. Rename output files"
        print_info "  6. Generate analysis report"
        print_info "  7. Clean up temporary files (none)"
    fi
    echo ""
}

# Main function
main() {
    # Display workflow summary
    show_workflow_summary
    
    # Parse arguments
    parse_arguments "$@"
    
    # Check dependencies
    check_dependencies
    
    # Preprocess VCF
    preprocess_vcf
    
    # Filter VCF
    filter_vcf
    
    # Run genotype conversion
    run_genotype_conversion
    
    # Generate report
    generate_report
    
    # Clean up temporary files
    cleanup_temp_files
    
    echo ""
    echo "=================================================="
    print_info "Analysis pipeline completed!"
    print_info "Completed at: $(date)"
    echo "=================================================="
    echo ""
    
    print_info "Output files:"
    for file in "${OUTPUT_PREFIX}".*; do
        if [[ -f "$file" ]]; then
            size=$(du -h "$file" | cut -f1)
            print_info "  - $file ($size)"
        fi
    done
    
    echo ""
}

# Run main function
main "$@"