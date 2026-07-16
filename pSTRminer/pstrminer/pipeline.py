"""
pSTRminer Pipeline Backend
Handles execution of HipSTR_configuration.sh and Polymorphism.sh,
with real-time log streaming for GUI or CLI use.
"""

import os
import sys
import subprocess
import threading
import shutil
import platform
import stat
from pathlib import Path


def get_scripts_dir() -> Path:
    """Return the path to the bundled scripts directory."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: _MEIPASS holds extracted files
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    return base / "scripts"


def _make_executable(path: Path):
    """Ensure a file has executable permission."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def prepare_scripts(work_dir: Path) -> Path:
    """
    Copy bundled scripts into work_dir/pstrminer_scripts so that
    run_TRF.sh can find trf409.legacylinux64 in its working directory.
    Returns the path to the scripts copy.
    """
    src = get_scripts_dir()
    dst = work_dir / "pstrminer_scripts"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for f in dst.iterdir():
        if f.suffix in (".sh",) or f.name.startswith("trf"):
            _make_executable(f)
    return dst


def stream_process(cmd: list, cwd: Path, env: dict,
                   log_callback, done_callback):
    """
    Run *cmd* in a background thread.
    log_callback(line: str)  — called for each stdout/stderr line
    done_callback(rc: int)   — called when process exits
    """
    def _run():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(cwd),
                env=env,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:
                log_callback(line.rstrip("\n"))
            proc.wait()
            done_callback(proc.returncode)
        except Exception as exc:
            log_callback(f"[ERROR] {exc}")
            done_callback(1)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


# ─────────────────────────────────────────────────────────────
#  Step 1 – HipSTR Configuration
# ─────────────────────────────────────────────────────────────

def run_hipstr_configuration(
    output_dir: str,
    genome_name: str = "",
    reference_file: str = "",
    trf_path: str = "",
    log_callback=print,
    done_callback=lambda rc: None,
):
    """
    Run HipSTR_configuration.sh inside *output_dir*.

    Provide exactly one of:
      genome_name    — UCSC identifier (e.g. "bosTau9")
      reference_file — path to a local FASTA

    Optional:
      trf_path       — path to a local TRF executable. If given, the pipeline
                       uses it instead of downloading TRF (for offline use).
    """
    work = Path(output_dir)
    work.mkdir(parents=True, exist_ok=True)

    scripts = prepare_scripts(work)
    config_sh = scripts / "HipSTR_configuration.sh"
    _make_executable(config_sh)

    if genome_name and reference_file:
        raise ValueError("Provide either genome_name or reference_file, not both.")
    if not genome_name and not reference_file:
        raise ValueError("Either genome_name or reference_file must be specified.")

    if genome_name:
        cmd = ["bash", str(config_sh), "-R", genome_name]
    else:
        ref = Path(reference_file).resolve()
        cmd = ["bash", str(config_sh), "--reference", str(ref)]

    env = os.environ.copy()
    env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")
    if trf_path:
        env["PSTRMINER_TRF"] = str(Path(trf_path).resolve())
        log_callback(f"[pSTRminer] Using local TRF: {env['PSTRMINER_TRF']}")

    log_callback(f"[pSTRminer] Working directory: {work}")
    log_callback(f"[pSTRminer] Command: {' '.join(cmd)}")

    # Run with cwd = the user's output directory so that reference_genome/
    # (and all results) are created there, NOT inside pstrminer_scripts/.
    # The script locates its own auxiliary scripts via BASH_SOURCE/SCRIPT_DIR,
    # so it works correctly regardless of the working directory.
    return stream_process(cmd, cwd=work, env=env,
                          log_callback=log_callback,
                          done_callback=done_callback)


# ─────────────────────────────────────────────────────────────
#  Step 2 – Polymorphism Analysis
# ─────────────────────────────────────────────────────────────

def run_polymorphism(
    output_dir: str,
    config_bed: str,
    input_vcf: str,
    output_prefix: str,
    needs_filter: bool = True,
    # Filtering parameters (only when needs_filter=True)
    min_call_qual: float = 0.9,
    max_call_flank_indel: float = 0.15,
    max_call_stutter: float = 0.15,
    min_call_allele_bias: float = -2.0,
    min_call_strand_bias: float = -2.0,
    log_callback=print,
    done_callback=lambda rc: None,
):
    """
    Run Polymorphism.sh.

    needs_filter=True  → Mode T (filter raw HipSTR VCF then analyse)
    needs_filter=False → Mode F (VCF already filtered, go straight to analysis)
    """
    work = Path(output_dir)
    work.mkdir(parents=True, exist_ok=True)

    scripts = prepare_scripts(work)
    poly_sh = scripts / "Polymorphism.sh"
    _make_executable(poly_sh)

    filter_script = scripts / "filter_vcf.py"

    cmd = [
        "bash", str(poly_sh),
        "-C", str(Path(config_bed).resolve()),
        "-I", str(Path(input_vcf).resolve()),
        "-O", str(Path(output_dir) / output_prefix),
        "-F", "T" if needs_filter else "F",
    ]

    if needs_filter:
        cmd += [
            "--filter-script", str(filter_script),
            "--min-call-qual",          str(min_call_qual),
            "--max-call-flank-indel",   str(max_call_flank_indel),
            "--max-call-stutter",       str(max_call_stutter),
            "--min-call-allele-bias",   str(min_call_allele_bias),
            "--min-call-strand-bias",   str(min_call_strand_bias),
        ]

    env = os.environ.copy()
    env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")

    log_callback(f"[pSTRminer] Working directory: {work}")
    log_callback(f"[pSTRminer] Command: {' '.join(cmd)}")

    # Run with cwd = output directory for consistency. Step 2 already writes
    # results via the absolute -O prefix, but running here keeps any
    # incidental intermediate files inside the user's output directory.
    return stream_process(cmd, cwd=work, env=env,
                          log_callback=log_callback,
                          done_callback=done_callback)
