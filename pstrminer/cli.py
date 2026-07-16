#!/usr/bin/env python3
"""
pSTRminer – Command-Line Interface
====================================
Usage
-----
  # Step 1: Generate HipSTR configuration (UCSC genome download)
  pstrminer config -o ./results -R bosTau9

  # Step 1: Generate HipSTR configuration (local FASTA)
  pstrminer config -o ./results --reference /path/to/genome.fa

  # Step 2: Polymorphism analysis (with VCF filtering)
  pstrminer poly -o ./results -C bosTau9.configuration.DitoHex.bed \
                 -I hipstr_raw.vcf.gz -O my_study -F T \
                 --min-call-qual 0.9 --max-call-flank-indel 0.15 \
                 --max-call-stutter 0.15 \
                 --min-call-allele-bias -2 --min-call-strand-bias -2

  # Step 2: Polymorphism analysis (pre-filtered VCF)
  pstrminer poly -o ./results -C config.bed -I filtered.vcf -O my_study -F F
"""

import argparse
import sys
import threading
from pstrminer.pipeline import run_hipstr_configuration, run_polymorphism


def _log(line: str):
    print(line, flush=True)


def _wait_done(event: threading.Event, rc_box: list):
    def cb(rc):
        rc_box.append(rc)
        event.set()
    return cb


# ── sub-command: config ───────────────────────────────────────
def cmd_config(args):
    if args.R and args.reference:
        print("Error: -R and --reference are mutually exclusive.", file=sys.stderr)
        sys.exit(1)
    if not args.R and not args.reference:
        print("Error: Either -R or --reference must be specified.", file=sys.stderr)
        sys.exit(1)

    done = threading.Event()
    rc_box = []
    run_hipstr_configuration(
        output_dir=args.output_dir,
        genome_name=args.R or "",
        reference_file=args.reference or "",
        trf_path=args.trf or "",
        log_callback=_log,
        done_callback=_wait_done(done, rc_box),
    )
    done.wait()
    sys.exit(rc_box[0] if rc_box else 1)


# ── sub-command: poly ─────────────────────────────────────────
def cmd_poly(args):
    needs_filter = args.F.upper() == "T"

    if needs_filter:
        missing = []
        for attr, name in [
            ("min_call_qual",        "--min-call-qual"),
            ("max_call_flank_indel", "--max-call-flank-indel"),
            ("max_call_stutter",     "--max-call-stutter"),
            ("min_call_allele_bias", "--min-call-allele-bias"),
            ("min_call_strand_bias", "--min-call-strand-bias"),
        ]:
            if getattr(args, attr) is None:
                missing.append(name)
        if missing:
            print(f"Error: When -F T the following params are required: {', '.join(missing)}",
                  file=sys.stderr)
            sys.exit(1)

    done = threading.Event()
    rc_box = []
    run_polymorphism(
        output_dir=args.output_dir,
        config_bed=args.C,
        input_vcf=args.I,
        output_prefix=args.O,
        needs_filter=needs_filter,
        min_call_qual=args.min_call_qual or 0.9,
        max_call_flank_indel=args.max_call_flank_indel or 0.15,
        max_call_stutter=args.max_call_stutter or 0.15,
        min_call_allele_bias=args.min_call_allele_bias or -2.0,
        min_call_strand_bias=args.min_call_strand_bias or -2.0,
        log_callback=_log,
        done_callback=_wait_done(done, rc_box),
    )
    done.wait()
    sys.exit(rc_box[0] if rc_box else 1)


# ── main parser ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="pstrminer",
        description="pSTRminer – Integrated STR Analysis Pipeline for Forensic Genetics",
    )
    parser.add_argument("--version", action="version", version="pSTRminer 1.0.1")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── config ──
    p_cfg = sub.add_parser("config",
        help="Step 1: Generate HipSTR configuration from a reference genome")
    p_cfg.add_argument("-o", "--output-dir", required=True, metavar="DIR",
        help="Output directory for all generated files")
    g = p_cfg.add_mutually_exclusive_group(required=True)
    g.add_argument("-R", metavar="GENOME",
        help="UCSC genome identifier (e.g. bosTau9, hg38, mm10)")
    g.add_argument("--reference", metavar="FASTA",
        help="Path to a local reference genome FASTA file")
    p_cfg.add_argument("--trf", metavar="PATH", default=None,
        help="Path to a local TRF executable (e.g. trf409.legacylinux64). "
             "If omitted, TRF is downloaded automatically. Use this for "
             "offline / firewalled environments that cannot reach GitHub.")
    p_cfg.set_defaults(func=cmd_config)

    # ── poly ──
    p_poly = sub.add_parser("poly",
        help="Step 2: Filter HipSTR VCF and calculate forensic parameters")
    p_poly.add_argument("-o", "--output-dir", required=True, metavar="DIR",
        help="Output directory")
    p_poly.add_argument("-C", required=True, metavar="BED",
        help="HipSTR configuration BED file")
    p_poly.add_argument("-I", required=True, metavar="VCF",
        help="Input VCF file from HipSTR")
    p_poly.add_argument("-O", required=True, metavar="PREFIX",
        help="Output file prefix")
    p_poly.add_argument("-F", required=True, choices=["T", "F"],
        help="T = filter raw VCF first; F = VCF already filtered")
    p_poly.add_argument("--min-call-qual",        type=float, metavar="FLOAT",
        help="Minimum call quality (default: 0.9)")
    p_poly.add_argument("--max-call-flank-indel", type=float, metavar="FLOAT",
        help="Maximum flanking indel rate (default: 0.15)")
    p_poly.add_argument("--max-call-stutter",     type=float, metavar="FLOAT",
        help="Maximum stutter rate (default: 0.15)")
    p_poly.add_argument("--min-call-allele-bias", type=float, metavar="FLOAT",
        help="Minimum allele bias (default: -2)")
    p_poly.add_argument("--min-call-strand-bias", type=float, metavar="FLOAT",
        help="Minimum strand bias (default: -2)")
    p_poly.set_defaults(func=cmd_poly)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
