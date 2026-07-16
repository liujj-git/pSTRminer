#!/usr/bin/env python3
"""
pstr_filter_vcf.py - call-level quality filtering for HipSTR VCF files.

Part of pSTRminer. Written for pSTRminer and released under the MIT License
together with the rest of the package.

This module applies per-genotype quality thresholds to a HipSTR VCF. A call
that fails any active threshold has its GT set to the missing value ("./."),
so that it is excluded from all downstream allele-frequency and forensic
parameter calculations. Loci and allele definitions are left untouched:
alleles that are no longer carried by any retained call simply never enter
the downstream tables, so removing them from the ALT list would be redundant.

The implementation deliberately uses only the Python 3 standard library. It
streams the VCF as text and therefore needs neither a tabix index nor any
third-party VCF parser.

Thresholds (all optional; a threshold left at its default is not applied):

    --min-call-depth           drop call if DP < value
    --min-call-qual            drop call if Q  < value
    --max-call-flank-indel     drop call if DFLANKINDEL / DP > value
    --max-call-stutter         drop call if DSTUTTER    / DP > value
    --min-call-allele-bias     drop call if AB < value
    --min-call-strand-bias     drop call if FS < value
    --min-loc-calls            drop locus if retained calls < value

In addition, a call whose PDP field reports zero depth for either allele is
always dropped, since such a genotype is not supported by data on both
alleles.
"""

import argparse
import collections
import gzip
import io
import sys

MISSING_GT = "./."
NULL_VALUES = (".", "", None)


# --------------------------------------------------------------------------
# input handling
# --------------------------------------------------------------------------

def open_vcf(path):
    """Return a text handle for a plain or gzip-compressed VCF, or stdin."""
    if path == "-":
        return sys.stdin
    with open(path, "rb") as probe:
        magic = probe.read(2)
    if magic == b"\x1f\x8b":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, "r", encoding="utf-8")


# --------------------------------------------------------------------------
# value helpers
# --------------------------------------------------------------------------

def as_float(value):
    """Parse a FORMAT value as float, or return None if it is absent."""
    if value in NULL_VALUES:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def is_missing_gt(value):
    """True when a GT subfield carries no genotype."""
    if value in NULL_VALUES:
        return True
    return set(value) <= set("./|")


# --------------------------------------------------------------------------
# the filter itself
# --------------------------------------------------------------------------

class CallFilter(object):
    """Evaluates one sample's call against the configured thresholds."""

    def __init__(self, opts):
        self.opts = opts

    def reason_to_drop(self, values):
        """
        Return a short reason string when the call must be dropped,
        or None when the call is retained.

        *values* maps FORMAT keys to their raw string values.
        """
        o = self.opts

        depth = as_float(values.get("DP"))
        if depth is not None and depth < o.min_call_depth:
            return "depth"

        qual = as_float(values.get("Q"))
        if qual is not None and qual < o.min_call_qual:
            return "quality"

        if self._allele_depth_is_zero(values.get("PDP")):
            return "allele_depth"

        if depth is not None and depth > 0:
            if o.max_call_flank_indel < 1:
                flank = as_float(values.get("DFLANKINDEL"))
                if flank is not None and flank / depth > o.max_call_flank_indel:
                    return "flank_indel"

            if o.max_call_stutter < 1:
                stutter = as_float(values.get("DSTUTTER"))
                if stutter is not None and stutter / depth > o.max_call_stutter:
                    return "stutter"

        if o.min_call_allele_bias > -100:
            bias = as_float(values.get("AB"))
            if bias is not None and bias < o.min_call_allele_bias:
                return "allele_bias"

        if o.min_call_strand_bias > -100:
            strand = as_float(values.get("FS"))
            if strand is not None and strand < o.min_call_strand_bias:
                return "strand_bias"

        return None

    @staticmethod
    def _allele_depth_is_zero(pdp):
        """True when PDP reports zero reads supporting either allele."""
        if pdp in NULL_VALUES:
            return False
        parts = pdp.split("|")
        if len(parts) != 2:
            return False
        depths = [as_float(p) for p in parts]
        if any(d is None for d in depths):
            return False
        return any(d == 0 for d in depths)


# --------------------------------------------------------------------------
# record processing
# --------------------------------------------------------------------------

def process_record(fields, call_filter, stats):
    """
    Filter every sample column of one VCF data line, in place.
    Returns the number of calls retained at this locus.
    """
    fmt_keys = fields[8].split(":")
    try:
        gt_index = fmt_keys.index("GT")
    except ValueError:
        # No genotypes to filter at this locus.
        return 0

    retained = 0
    for col in range(9, len(fields)):
        subfields = fields[col].split(":")
        if is_missing_gt(subfields[gt_index] if gt_index < len(subfields) else None):
            continue

        values = dict(zip(fmt_keys, subfields))
        reason = call_filter.reason_to_drop(values)

        if reason is None:
            retained += 1
        else:
            subfields[gt_index] = MISSING_GT
            fields[col] = ":".join(subfields)
            stats[reason] += 1

    return retained


def run(opts, source, sink, report):
    call_filter = CallFilter(opts)
    stats = collections.defaultdict(int)
    loci_in = 0
    loci_out = 0

    for line in source:
        if line.startswith("#"):
            sink.write(line)
            continue

        line = line.rstrip("\n")
        if not line:
            continue

        loci_in += 1
        fields = line.split("\t")
        if len(fields) < 10:
            sink.write(line + "\n")
            loci_out += 1
            continue

        retained = process_record(fields, call_filter, stats)
        if retained < opts.min_loc_calls:
            continue

        sink.write("\t".join(fields) + "\n")
        loci_out += 1

    dropped = sum(stats.values())
    report.write("[pstr-filter] loci read      : %d\n" % loci_in)
    report.write("[pstr-filter] loci written   : %d\n" % loci_out)
    report.write("[pstr-filter] calls dropped  : %d\n" % dropped)
    for reason in sorted(stats):
        report.write("[pstr-filter]   %-14s: %d\n" % (reason, stats[reason]))


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="Apply call-level quality filters to a HipSTR VCF. "
                    "Failing genotypes are set to ./. and the VCF is written "
                    "to stdout.")
    p.add_argument("--vcf", required=True, metavar="FILE",
                   help="Input VCF (plain or gzip-compressed; '-' for stdin)")
    p.add_argument("--min-call-depth", type=float, default=0.0, metavar="INT",
                   help="Drop a call if DP is below this value (default: 0)")
    p.add_argument("--min-call-qual", type=float, default=0.0, metavar="FLOAT",
                   help="Drop a call if Q is below this value (default: 0)")
    p.add_argument("--max-call-flank-indel", type=float, default=1.0,
                   metavar="FLOAT",
                   help="Drop a call if DFLANKINDEL/DP exceeds this value "
                        "(default: 1, i.e. not applied)")
    p.add_argument("--max-call-stutter", type=float, default=1.0,
                   metavar="FLOAT",
                   help="Drop a call if DSTUTTER/DP exceeds this value "
                        "(default: 1, i.e. not applied)")
    p.add_argument("--min-call-allele-bias", type=float, default=-100.0,
                   metavar="FLOAT",
                   help="Drop a call if AB is below this value "
                        "(default: -100, i.e. not applied)")
    p.add_argument("--min-call-strand-bias", type=float, default=-100.0,
                   metavar="FLOAT",
                   help="Drop a call if FS is below this value "
                        "(default: -100, i.e. not applied)")
    p.add_argument("--min-loc-calls", type=int, default=0, metavar="INT",
                   help="Drop a locus if fewer calls than this survive "
                        "(default: 0)")
    return p


def main():
    opts = build_parser().parse_args()
    source = open_vcf(opts.vcf)
    try:
        run(opts, source, sys.stdout, sys.stderr)
    finally:
        if source is not sys.stdin:
            source.close()


if __name__ == "__main__":
    main()
