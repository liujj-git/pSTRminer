from setuptools import setup, find_packages
from pathlib import Path

long_desc = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="pstrminer",
    version="1.0.0",
    author="pSTRminer Team",
    description="Integrated STR Analysis Pipeline for Forensic Genetics",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/Sunlab-forensicsysu/pSTRminer",
    packages=find_packages(),
    package_data={
        "pstrminer": [],
        # scripts are at the top-level scripts/ directory
        "": ["scripts/*"],
    },
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[],        # Tkinter is part of stdlib; no external deps for GUI
    extras_require={
        "package": ["pyinstaller>=5.0"],
    },
    entry_points={
        "console_scripts": [
            "pstrminer = pstrminer.cli:main",
        ],
        "gui_scripts": [
            "pstrminer-gui = pstrminer.gui:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
