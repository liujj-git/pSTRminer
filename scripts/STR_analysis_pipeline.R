#!/usr/bin/env Rscript
# Integrated STR Analysis Pipeline
# Combines Asequence.R, copynumberGT.R and forensic_parameter.R functionality
# Author: R Script Integration Assistant
# Version: 2.0

# Load required libraries
library(tidyr)
library(vcfR)
library(data.table)

# Set parameters
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript STR_analysis_pipeline.R <vcf_file> <bed_file>", call. = FALSE)
}

vcf_file <- args[1]
bed_file <- args[2]

cat("========================================\n")
cat("Starting STR Analysis Pipeline\n")
cat("========================================\n")

# ==================== Part 1: Asequence.R ====================
cat("\n[Step 1/3] Running Asequence.R - Analyzing allele sequences\n")

# Read VCF
cat("Reading VCF file:", vcf_file, "\n")
raw_vcf <- read.vcfR(vcf_file)

# Read period_size from bed file
cat("Reading BED file:", bed_file, "\n")
period_size <- read.table(bed_file)[, c(6, 4)]

# Create allele sequence data
allele_ladder <- data.frame(
  "locus" = raw_vcf@fix[, 3],
  "Ref" = raw_vcf@fix[, 4],
  "Alt" = raw_vcf@fix[, 5]
)

allele_ladder <- na.omit(gather(allele_ladder, key = "allele_group", value = "sequence", -locus))

tem1 <- allele_ladder[!grepl(",", allele_ladder$sequence), ]
tem2 <- allele_ladder[grepl(",", allele_ladder$sequence), ]

cat("Starting allele sequence analysis...\n")
if (nrow(tem2) > 0) {
  tem3 <- do.call(rbind, apply(tem2, 1, function(x) {
    alt_allele <- unlist(strsplit(x[3], ","))
    data.frame(
      "locus" = x[1],
      "allele_group" = 1:length(alt_allele),
      "sequence" = alt_allele,
      row.names = NULL
    )
  }))
  cat("Completed allele sequence analysis\n")
} else {
  tem3 <- data.frame()
  cat("No multi-alleles to analyze\n")
}

tem1 <- rbind(tem1, tem3)
tem1$allele_group[tem1$allele_group == "Ref"] <- 0
tem1$allele_group[tem1$allele_group == "Alt"] <- 1
tem1$allele_length <- nchar(tem1$sequence)
tem1$period_size <- period_size[match(tem1$locus, period_size[, 1]), 2]
tem1$copy_number <- ifelse(tem1$allele_length %% tem1$period_size != 0,
                           paste(tem1$allele_length %/% tem1$period_size,
                                 tem1$allele_length %% tem1$period_size, sep = "."),
                           tem1$allele_length %/% tem1$period_size)
tem1$copynumber_label <- paste(tem1$locus, tem1$copy_number, sep = "_")
tem2 <- as.data.frame(table(tem1$copynumber_label))
tem2[, 1] <- as.character(tem2[, 1])
tem2 <- tem2[tem2$Freq != 1, 1]

cat("Starting copy number analysis...\n")
setDT(tem1)
tem1[!tem1$copynumber_label %in% tem2, copynumber_label := copy_number]
if (length(tem2) > 0) {
  tem1[tem1$copynumber_label %in% tem2, copynumber_label := {
    paste(copy_number, seq_along(copy_number), sep = "_")
  }, by = copynumber_label]
}
cat("Completed copy number analysis\n")

allele_ladder <- tem1
allele_ladder <- allele_ladder[order(allele_ladder$locus), ]

write.table(allele_ladder, file = "allele_sequence.txt",
            col.names = TRUE, row.names = FALSE, quote = FALSE, sep = "\t")

cat("Generated file: allele_sequence.txt\n")

# ==================== Part 2: copynumberGT.R ====================
cat("\n[Step 2/3] Running copynumberGT.R - Converting genotypes to copy numbers\n")

# Read allele_sequence.txt
if (file.exists("allele_sequence.txt")) {
  allele_ladder <- read.table("allele_sequence.txt", header = TRUE)
  cat("Reading allele_sequence.txt\n")
} else {
  stop("Error: allele_sequence.txt file not found", call. = FALSE)
}

# Replace GT with copynumber_label
gt_df <- data.frame("locus" = raw_vcf@fix[, 3], as.data.frame(extract.gt(raw_vcf)))
cat("Analyzing all loci\n")

gt_df <- na.omit(gather(gt_df, key = "sample", value = "GT", -locus))
gt_df <- separate(gt_df, col = "GT", into = c("allele1", "allele2"), sep = "\\|")
cat("Starting genotype conversion\n")

gt_df$A1_label <- paste(gt_df$locus, gt_df$allele1, sep = "@")
gt_df$A2_label <- paste(gt_df$locus, gt_df$allele2, sep = "@")
allele_ladder$label <- paste(allele_ladder$locus, allele_ladder$allele_group, sep = "@")

gt_df$cn1 <- allele_ladder$copynumber_label[match(gt_df$A1_label, allele_ladder$label)]
gt_df$cn2 <- allele_ladder$copynumber_label[match(gt_df$A2_label, allele_ladder$label)]
gt_df$l1 <- allele_ladder$copy_number[match(gt_df$A1_label, allele_ladder$label)]
gt_df$l2 <- allele_ladder$copy_number[match(gt_df$A2_label, allele_ladder$label)]

# Ensure copy numbers are ordered (smaller first)
l1_numeric <- suppressWarnings(as.numeric(gsub("\\..*", "", gt_df$l1)))
l2_numeric <- suppressWarnings(as.numeric(gsub("\\..*", "", gt_df$l2)))

# Handle cases that cannot be converted to numeric
l1_numeric[is.na(l1_numeric)] <- 0
l2_numeric[is.na(l2_numeric)] <- 0

# Swap order when l1 > l2
swap_idx <- l1_numeric > l2_numeric
temp_cn1 <- gt_df$cn1[swap_idx]
gt_df$cn1[swap_idx] <- gt_df$cn2[swap_idx]
gt_df$cn2[swap_idx] <- temp_cn1

gt_df <- gt_df[, c("locus", "sample", "cn1", "cn2")]
colnames(gt_df) <- c("locus", "sample", "allele1", "allele2")
gt_df <- unite(gt_df, "GT", c("allele1", "allele2"), sep = ",")
gt_df <- spread(gt_df, key = "sample", value = "GT")
cat("Completed genotype conversion\n")

write.table(gt_df, file = "GT.copynumber.txt",
            col.names = TRUE, row.names = FALSE, quote = FALSE, sep = "\t")

cat("Generated file: GT.copynumber.txt\n")

# ==================== Part 3: forensic_parameter.R ====================
cat("\n[Step 3/3] Running forensic_parameter.R - Calculating forensic parameters\n")

# Define helper functions
identify_het <- function(x) {
  allele <- unlist(strsplit(x[1], ","))
  if (length(unique(allele)) == 1) {
    return("Homo")
  } else {
    return("Het")
  }
}

MPvalue <- function(freq = "") {
  if (length(freq) == 1) {
    return(0)
  } else {
    Frequency <- c()
    for (i in 1:length(freq)) {
      Frequency <- c(Frequency, freq[i] * freq[i])
      for (j in (i + 1):length(freq)) {
        if (j > length(freq)) break
        Frequency <- c(Frequency, 2 * freq[i] * freq[j])
      }
    }
    mp <- sum(Frequency * Frequency)
    return(mp)
  }
}

PD_value <- function(x) {
  p1 <- 0
  p2 <- 0
  if (length(x) == 1) {
    return(0)
  } else {
    for (i in seq_along(x)) {
      p1 <- p1 + (x[i])^2
      p2 <- p2 + (x[i])^4
    }
    PD <- 1 - 2 * p1^2 + p2
    return(PD)
  }
}

PE2_value <- function(x) {
  p1 <- 0
  p2 <- 0
  if (length(x) == 1) {
    return(0)
  } else {
    for (i in seq_along(x)) {
      p1 <- p1 + ((x[i])^2) * ((1 - x[i])^2)
      if (i != length(x)) {
        for (j in (i + 1):length(x)) {
          p2 <- p2 + 2 * x[i] * x[j] * ((1 - x[i] - x[j])^2)
        }
      }
    }
    PE2 <- p1 + p2
    return(PE2)
  }
}

PE3_value <- function(x) {
  p1 <- 0
  p2 <- 0
  if (length(x) == 1) {
    return(0)
  } else {
    for (i in seq_along(x)) {
      p1 <- p1 + x[i] * ((1 - x[i])^2)
      if (i != length(x)) {
        for (j in (i + 1):length(x)) {
          p2 <- p2 + 0.5 * (x[i]^2) * (x[j]^2) * (4 - 3 * x[i] - 3 * x[j])
        }
      }
    }
    PE3 <- p1 - p2
    return(PE3)
  }
}

PIC_value <- function(x) {
  p1 <- 0
  p2 <- 0
  if (length(x) == 1) {
    return(0)
  } else {
    for (i in seq_along(x)) {
      p1 <- p1 + (x[i])^2
      p2 <- p2 + (x[i])^4
    }
    PIC <- 1 - p1 - p1^2 + p2
    return(PIC)
  }
}

Ae_value <- function(x) {
  # Effective number of alleles: the reciprocal of the expected homozygosity,
  # Ae = 1 / sum(p_i^2). A monomorphic locus gives sum(p_i^2) = 1 and so
  # Ae = 1, which is the correct interpretation (a single effective allele).
  # Note this is derived from the allele frequencies directly, not from He:
  # He above carries the N/(N-1) unbiased correction, so 1 - He is not the
  # homozygosity.
  return(1 / sum(x^2))
}

# Calculate forensic parameters: N,Na,Ho,He,MP,PD,PE2,PE3,PIC,Ae
forensic_parameters_calculator <- function(x) {
  locus <- x[1]
  GT <- na.omit(x[-1])
  if (length(GT) == 0) {
    return(data.frame(
      "locus" = locus,
      "N" = 0,
      "Na" = 0,
      "Ho" = "",
      "He" = "",
      "MP" = "",
      "PD" = "",
      "PE2" = "",
      "PE3" = "",
      "PIC" = "",
      "Ae" = "",
      row.names = NULL
    ))
  } else {
    alleles <- unlist(strsplit(GT, ","))
    allele_number <- length(alleles)
    allele_type <- length(unique(alleles))
    GT_table <- as.data.frame(table(GT))
    Het_grepl <- apply(GT_table, 1, identify_het)
    Observe_Het <- round(sum(GT_table[which(Het_grepl == "Het"), 2]) / sum(GT_table[, 2]), 4)
    allele_table <- as.data.frame(table(alleles))
    Expect_Het <- round(allele_number / (allele_number - 1) *
                          (1 - sum((allele_table[, 2] / sum(allele_table[, 2]))^2)), 4)
    allele_freq <- allele_table[, 2] / sum(allele_table[, 2])
    PD <- round(PD_value(allele_freq), 4)
    PE2 <- round(PE2_value(allele_freq), 4)
    PE3 <- round(PE3_value(allele_freq), 4)
    PIC <- round(PIC_value(allele_freq), 4)
    MP <- round(MPvalue(allele_freq), 4)
    Ae <- round(Ae_value(allele_freq), 4)
    
    return(data.frame(
      "locus" = locus,
      "N" = allele_number,
      "Na" = allele_type,
      "Ho" = Observe_Het,
      "He" = Expect_Het,
      "MP" = MP,
      "PD" = PD,
      "PE2" = PE2,
      "PE3" = PE3,
      "PIC" = PIC,
      "Ae" = Ae,
      row.names = NULL
    ))
  }
}

# Calculate allele frequency
allele_freq_calculator <- function(x) {
  locus <- x[1]
  GT <- na.omit(x[-1])
  if (length(GT) == 0) {
    return(data.frame(
      "locus" = locus,
      "allele" = "",
      "frequency" = "",
      row.names = NULL
    ))
  } else {
    alleles <- unlist(strsplit(GT, ","))
    allele_table <- as.data.frame(table(alleles))
    allele_freq <- allele_table[, 2] / sum(allele_table[, 2])
    allele_df <- data.frame(
      "locus" = locus,
      "allele" = as.character(allele_table[, 1]),
      "frequency" = round(allele_freq, 3),
      row.names = NULL
    )
    return(allele_df)
  }
}

# Read data
input_file <- "GT.copynumber.txt"
cat("Reading file:", input_file, "\n")
input <- read.table(input_file, header = TRUE, check.names = FALSE)

# Calculate forensic parameters
cat("Calculating forensic parameters...\n")
output1 <- do.call(rbind, apply(input, 1, forensic_parameters_calculator))
output2 <- do.call(rbind, apply(input, 1, allele_freq_calculator))

# Output results
write.table(output1, file = "forensic_parameters.txt",
            col.names = TRUE, row.names = FALSE, quote = FALSE, sep = "\t")
write.table(output2, file = "allele_freq.txt",
            col.names = TRUE, row.names = FALSE, quote = FALSE, sep = "\t")

# Generate summary statistics
cat("Generating summary statistics...\n")
summary_file <- "analysis_summary.txt"

# Calculate basic statistics
total_loci <- nrow(output1)
total_samples <- ncol(input) - 1  # minus the locus column

# Calculate average heterozygosity
avg_Ho <- mean(as.numeric(output1$Ho[output1$Ho != ""]), na.rm = TRUE)
avg_He <- mean(as.numeric(output1$He[output1$He != ""]), na.rm = TRUE)

# Calculate average PD and PIC
avg_PD <- mean(as.numeric(output1$PD[output1$PD != ""]), na.rm = TRUE)
avg_PIC <- mean(as.numeric(output1$PIC[output1$PIC != ""]), na.rm = TRUE)
avg_Ae <- mean(as.numeric(output1$Ae[output1$Ae != ""]), na.rm = TRUE)

# Write summary
writeLines(c(
  "========================================",
  "STR Analysis Pipeline Summary",
  paste("Generated:", Sys.time()),
  "========================================",
  "",
  paste("Total loci analyzed:", total_loci),
  paste("Total samples:", total_samples),
  "",
  "Average statistics:",
  paste("  Average observed heterozygosity (Ho):", round(avg_Ho, 4)),
  paste("  Average expected heterozygosity (He):", round(avg_He, 4)),
  paste("  Average discrimination power (PD):", round(avg_PD, 4)),
  paste("  Average polymorphism information content (PIC):", round(avg_PIC, 4)),
  paste("  Average effective number of alleles (Ae):", round(avg_Ae, 4)),
  "",
  "Output files generated:",
  "  1. allele_sequence.txt - Allele sequence information",
  "  2. GT.copynumber.txt - Copy number genotypes",
  "  3. forensic_parameters.txt - Forensic parameters",
  "  4. allele_freq.txt - Allele frequencies",
  "  5. analysis_summary.txt - This summary file",
  "",
  "Pipeline completed successfully!",
  "========================================"
), con = summary_file)

cat("========================================\n")
cat("Analysis completed! Generated files:\n")
cat("1. allele_sequence.txt - Allele sequence information\n")
cat("2. GT.copynumber.txt - Copy number genotypes\n")
cat("3. forensic_parameters.txt - Forensic parameters\n")
cat("4. allele_freq.txt - Allele frequencies\n")
cat("5. analysis_summary.txt - Analysis summary\n")
cat("========================================\n")