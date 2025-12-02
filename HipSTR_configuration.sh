#!/bin/bash
set -e  # Exit on any error

# HipSTR Reference Generation Pipeline
# Integrated version with -R and -reference parameters

# Default configuration
GENOME=""
REFERENCE_FILE=""
THREADS_TRF=30
THREADS_PYTHON=40
SCRIPT_DIR=$(pwd)  # Save current directory

# Function to display usage
usage() {
    echo "Usage: $0 -R <reference_genome_name> OR $0 --reference <path_to_reference.fa>"
    echo ""
    echo "Options:"
    echo "  -R <name>          : Reference genome name (e.g., mm10, hg38)"
    echo "                       Downloads from UCSC"
    echo "  --reference <path> : Path to local reference genome FASTA file"
    echo "                       Uses existing file instead of downloading"
    echo ""
    echo "Examples:"
    echo "  $0 -R mm10                    # Download mm10 from UCSC"
    echo "  $0 --reference /path/to/my.fa # Use local reference file"
    echo ""
    echo "Note: -R and --reference are mutually exclusive"
    exit 1
}

# Function to parse command line arguments
parse_arguments() {
    # Check if no arguments provided
    if [ $# -eq 0 ]; then
        echo "Error: No arguments provided"
        usage
    fi
    
    # Parse arguments manually
    while [[ $# -gt 0 ]]; do
        case $1 in
            -R)
                if [[ -z "$2" ]] || [[ "$2" == -* ]]; then
                    echo "Error: -R requires a genome name"
                    usage
                fi
                GENOME="$2"
                shift 2
                ;;
            --reference)
                if [[ -z "$2" ]] || [[ "$2" == -* ]]; then
                    echo "Error: --reference requires a file path"
                    usage
                fi
                REFERENCE_FILE="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                echo "Error: Unknown option: $1"
                usage
                ;;
        esac
    done
    
    # Check if both options are used
    if [[ -n "$GENOME" ]] && [[ -n "$REFERENCE_FILE" ]]; then
        echo "Error: Cannot use both -R and --reference options simultaneously"
        usage
    fi
    
    # Check if neither option is used
    if [[ -z "$GENOME" ]] && [[ -z "$REFERENCE_FILE" ]]; then
        echo "Error: Either -R or --reference must be specified"
        usage
    fi
    
    # Determine genome name if using --reference
    if [[ -n "$REFERENCE_FILE" ]]; then
        if [[ ! -f "$REFERENCE_FILE" ]]; then
            echo "Error: Reference file not found: $REFERENCE_FILE"
            exit 1
        fi
        
        # Extract genome name from filename
        GENOME=$(basename "$REFERENCE_FILE" .fa)
        GENOME=$(basename "$GENOME" .fasta)
        GENOME=$(basename "$GENOME" .fna)
        echo "Using local reference file: $REFERENCE_FILE"
        echo "Genome name derived from filename: $GENOME"
    else
        echo "Downloading reference genome: $GENOME"
    fi
    
    echo "Using genome name: $GENOME"
}

# Function to check dependencies
check_dependencies() {
    echo "Checking dependencies..."
    
    local deps=("python2" "bedtools" "faidx" "wget" "git")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            missing+=("$dep")
            echo "ERROR: $dep"
        else
            echo "OK: $dep"
        fi
    done
    
    if [[ ${#missing[@]} -ne 0 ]]; then
        echo "ERROR: Missing dependencies: ${missing[*]}"
        exit 1
    fi
    
    echo "All dependencies satisfied!"
}

# Function to check and download software if needed
setup_software() {
    echo "=================================================="
    echo "Step 1: Setting Up Software"
    echo "=================================================="
    
    # Check if TRF is already installed in PATH
    if command -v trf409.legacylinux64 &> /dev/null || [[ -f "trf409.legacylinux64" ]]; then
        echo "TRF already available, skipping download..."
        
        # If not in current directory but in PATH, create a local copy
        if [[ ! -f "trf409.legacylinux64" ]] && command -v trf409.legacylinux64 &> /dev/null; then
            TRF_PATH=$(which trf409.legacylinux64)
            echo "Creating symbolic link to TRF from: $TRF_PATH"
            ln -sf "$TRF_PATH" "trf409.legacylinux64"
        fi
    else
        echo "Downloading Tandem Repeats Finder (TRF)..."
        wget -q https://github.com/Benson-Genomics-Lab/TRF/releases/download/v4.09.1/trf409.legacylinux64
        chmod 755 trf409.legacylinux64
        echo "TRF downloaded"
    fi
    
    # Download HipSTR references only if not already present
    if [[ ! -d "HipSTR-references" ]]; then
        echo "Downloading HipSTR references..."
        git clone https://github.com/HipSTR-Tool/HipSTR-references.git
        chmod -R 755 HipSTR-references/scripts/
    else
        echo "HipSTR-references already exists, skipping download..."
    fi
    
    echo "Software setup completed!"
}

# Function to setup reference genome (download or use local)
setup_reference_genome() {
    echo "=================================================="
    echo "Step 2: Setting Up Reference Genome"
    echo "=================================================="
    
    # Create main directory structure
    mkdir -p reference_genome
    cd reference_genome
    
    # Create genome-specific subdirectories
    mkdir -p raw_fasta/${GENOME} trf_results/${GENOME} fixed_trf_results/${GENOME}
    
    # Check if we're using a local reference file
    if [[ -n "$REFERENCE_FILE" ]]; then
        echo "Using local reference file: $REFERENCE_FILE"
        
        # Check if reference file exists
        if [[ ! -f "$REFERENCE_FILE" ]]; then
            echo "Error: Reference file not found: $REFERENCE_FILE"
            exit 1
        fi
        
        # Copy or link the reference file
        if [[ ! -f "${GENOME}.fa" ]]; then
            echo "Linking reference file to ${GENOME}.fa..."
            ln -sf "$REFERENCE_FILE" "${GENOME}.fa"
        fi
    else
        # Download from UCSC
        if [[ ! -f "${GENOME}.fa" ]]; then
            echo "Downloading ${GENOME} reference genome..."
            
            # Try multiple mirrors for better download speed
            local mirrors=(
                "https://hgdownload.soe.ucsc.edu/goldenPath"
                "https://mirrors.tuna.tsinghua.edu.cn/goldenPath"
                "https://mirrors.ustc.edu.cn/goldenPath"
            )
            
            local downloaded=0
            for mirror in "${mirrors[@]}"; do
                echo "Trying mirror: $mirror"
                wget -c -t 3 -T 30 --retry-connrefused -O "${GENOME}.fa.gz" "${mirror}/$GENOME/bigZips/$GENOME.fa.gz"
                
                if [[ $? -eq 0 ]] && [[ -f "${GENOME}.fa.gz" ]] && [[ $(wc -c < "${GENOME}.fa.gz" 2>/dev/null || echo 0) -gt 1000000 ]]; then
                    echo "Download successful from $mirror"
                    downloaded=1
                    break
                else
                    echo "Download failed or file too small, trying next mirror..."
                    rm -f "${GENOME}.fa.gz"
                fi
            done
            
            if [[ $downloaded -eq 1 ]]; then
                echo "Unzipping ${GENOME}.fa.gz..."
                gunzip -f "${GENOME}.fa.gz"
            else
                echo "Error: All download attempts failed."
                echo "Please manually download ${GENOME}.fa and place it in the reference_genome directory."
                exit 1
            fi
        else
            echo "Reference genome ${GENOME}.fa already exists, skipping download..."
        fi
    fi
    
    cd ..
    echo "Reference genome setup completed!"
}

# Function to prepare TRF for execution
prepare_trf() {
    echo "Preparing TRF for execution..."
    
    # Ensure trf is available in the reference_genome directory
    cd reference_genome
    
    if [[ ! -f "trf409.legacylinux64" ]]; then
        echo "Creating TRF symbolic link in reference_genome directory..."
        ln -sf "$SCRIPT_DIR/trf409.legacylinux64" "trf409.legacylinux64"
        chmod +x trf409.legacylinux64
    fi
    
    cd ..
    echo "TRF preparation completed!"
}

# Function to run HipSTR configuration
run_hipstr_configuration() {
    echo "=================================================="
    echo "Step 3: Running HipSTR Configuration Pipeline for $GENOME"
    echo "=================================================="
    
    cd reference_genome
    
    echo "Substep 1: Splitting reference genome by chromosome..."
    cd raw_fasta/${GENOME}
    faidx -x ../../${GENOME}.fa
    cd ../..
    
    # Make sure TRF executable is in current directory
    echo "Ensuring TRF is available in current directory..."
    if [[ ! -f "trf409.legacylinux64" ]]; then
        ln -sf "$SCRIPT_DIR/trf409.legacylinux64" "trf409.legacylinux64"
        chmod +x trf409.legacylinux64
    fi
    
    echo "Substep 2: Running Tandem Repeats Finder (TRF) on all chromosomes..."
    # Run TRF with proper environment
    for fasta_file in ./raw_fasta/${GENOME}/*.fa; do
        if [[ -f "$fasta_file" ]]; then
            chrom=$(basename "$fasta_file" .fa)
            echo "./raw_fasta/${GENOME}/$chrom.fa ./trf_results/${GENOME} 5"
        fi
    done | xargs -L 1 -P $THREADS_TRF "$SCRIPT_DIR/HipSTR-references/scripts/run_TRF.sh"
    
    echo "Substep 3: Filtering TRF results and fixing entries..."
    for trf_file in ./trf_results/${GENOME}/*.fa; do
        if [[ -f "$trf_file" ]]; then
            chrom=$(basename "$trf_file" .fa)
            echo "$SCRIPT_DIR/HipSTR-references/scripts/fix_trf_output.py ./trf_results/${GENOME}/$chrom.fa ./fixed_trf_results/${GENOME}/$chrom.fa"
        fi
    done | xargs -L 1 -P $THREADS_PYTHON python2
    
    echo "Substep 4: Reformatting and filtering TRF entries..."
    files=""
    for fixed_file in ./fixed_trf_results/${GENOME}/*.fa; do
        if [[ -f "$fixed_file" ]]; then
            chrom=$(basename "$fixed_file" .fa)
            files="$files,./fixed_trf_results/${GENOME}/$chrom.fa"
        fi
    done
    
    if [[ -z "$files" ]]; then
        echo "Error: No fixed TRF files found for genome ${GENOME}"
        echo "Please check if TRF ran successfully."
        exit 1
    fi
    
    files=$(echo $files | sed "s/,//")
    python2 "$SCRIPT_DIR/HipSTR-references/scripts/trf_parser.py" $files > ./filtered_repeats.${GENOME}.bed
    bedtools sort -i ./filtered_repeats.${GENOME}.bed > ./filtered_repeats.${GENOME}.sorted.bed
    
    echo "Substep 5: Merging overlapping STRs and filtering..."
    python2 "$SCRIPT_DIR/HipSTR-references/scripts/analyze_overlaps.py" ./filtered_repeats.${GENOME}.sorted.bed ./pass.${GENOME} ./fail.${GENOME}
    
    echo "Substep 6: Removing entries near failed merge regions..."
    bedtools window -w 10 -a ./pass.${GENOME} -b ./fail.${GENOME} -v > pass.${GENOME}.r2
    
    echo "Substep 7: Extracting high-quality STR entries..."
    bedtools merge -i ./pass.${GENOME}.r2 -c 4,6 -o collapse -d 10 | grep -v "," > ./pass.${GENOME}.r3
    bedtools merge -i ./pass.${GENOME}.r2 -c 4,4,4,6 -o collapse,count_distinct,distinct,collapse -d 10 | grep "," | awk '$5 == 1' | awk -v OFS="\t" '{print $1, $2, $3, $6, $7}' | sed "s/,/\//g" >> ./pass.${GENOME}.r3
    
    echo "Substep 8: Constructing final reference..."
    cat ./pass.${GENOME}.r3 | bedtools sort | awk -v OFS="\t" '{print $1, $2, $3, $4, ($3-$2+1)/$4, "'${GENOME}'_STR_"NR, $5}' > ${GENOME}.configuration.bed
    
    echo "Substep 9: Cleaning temporary files..."
    rm -f ./fail.${GENOME} ./filtered_repeats.${GENOME}.bed ./filtered_repeats.${GENOME}.sorted.bed
    rm -f ./pass.${GENOME} ./pass.${GENOME}.r2 ./pass.${GENOME}.r3
    
    echo "Substep 10: Removing mononucleotide repeats..."
    awk '{if($4!="1")print}' ${GENOME}.configuration.bed > ${GENOME}.configuration.DitoHex.bed
    
    cd ..
    
    echo "HipSTR configuration completed for $GENOME!"
}

# Function to display summary
display_summary() {
    echo "=================================================="
    echo "Pipeline Completed Successfully!"
    echo "Completed at: $(date)"
    echo "=================================================="
    
    if [[ -f "reference_genome/${GENOME}.configuration.DitoHex.bed" ]]; then
        STR_COUNT=$(wc -l < "reference_genome/${GENOME}.configuration.DitoHex.bed")
        echo "Generated ${STR_COUNT} STR regions for ${GENOME} in:"
        echo "  - reference_genome/${GENOME}.configuration.bed (all STRs)"
        echo "  - reference_genome/${GENOME}.configuration.DitoHex.bed (filtered, no mononucleotides)"
    else
        echo "ERROR: Final output file not found!"
        exit 1
    fi
    
    echo ""
    echo "Output file format:"
    echo "  Column 1: Chromosome"
    echo "  Column 2: Start position"
    echo "  Column 3: End position" 
    echo "  Column 4: Motif length"
    echo "  Column 5: Number of repeats"
    echo "  Column 6: STR ID"
    echo "  Column 7: Motif sequence"
}

# Main execution flow
main() {
    echo "=================================================="
    echo "HipSTR Reference Generation Pipeline"
    echo "Starting at: $(date)"
    echo "=================================================="
    
    # Parse command line arguments
    parse_arguments "$@"
    
    echo "Working directory: $(pwd)"
    echo ""
    
    # Run all steps
    check_dependencies
    setup_software
    setup_reference_genome
    prepare_trf
    run_hipstr_configuration
    display_summary
}

# Run main function with all arguments
main "$@"