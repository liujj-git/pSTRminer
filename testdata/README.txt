pSTRminer test dataset
======================

Generated : 2026-07-16 13:58:52

Contents
--------
test.vcf                 10 samples x 1000 loci (subset of the source VCF)
test.config.DitoHex.bed  1000 config rows, matching the loci in test.vcf

The config has been subset to exactly the loci present in test.vcf, because
STR_analysis_pipeline.R joins the two on the locus ID.

How to run
----------
Mode F (input already filtered):

  ./pSTRminer poly \
    -o ./test_output \
    -C test.config.DitoHex.bed \
    -I test.vcf \
    -O smoke_test \
    -F F

Mode T (filter first):

  ./pSTRminer poly \
    -o ./test_output \
    -C test.config.DitoHex.bed \
    -I test.vcf \
    -O smoke_test \
    -F T \
    --min-call-qual 0.9 \
    --max-call-flank-indel 0.15 \
    --max-call-stutter 0.15 \
    --min-call-allele-bias -2 \
    --min-call-strand-bias -2

Expected output in ./test_output/:
  smoke_test.filtered.vcf           (Mode T only)
  smoke_test.allele_sequence.txt
  smoke_test.GT.copynumber.txt
  smoke_test.forensic_parameters.txt
  smoke_test.allele_freq.txt
  smoke_test.analysis_report.txt

Check that forensic_parameters.txt has a column named PD (not DP).
