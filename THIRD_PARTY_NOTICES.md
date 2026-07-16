# Third-Party Notices

pSTRminer is distributed under the MIT License (see `LICENSE`). It bundles and
depends on the third-party components listed below. Each remains the property of
its respective copyright holders and is governed by its own licence.

---

## Bundled components

The following auxiliary scripts are redistributed unmodified in `scripts/` so
that pSTRminer can run offline without a separate download step.

### HipSTR-references

- Files: `run_TRF.sh`, `fix_trf_output.py`, `trf_parser.py`, `analyze_overlaps.py`
- Source: https://github.com/HipSTR-Tool/HipSTR-references
- Licence: MIT

```
MIT License

Copyright (c) 2017 HipSTR-Tool

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## External tools (not bundled)

These tools are obtained or installed by the user, or downloaded at run time.
They are not redistributed as part of pSTRminer, and their licences apply
independently.

| Tool | Licence | Source |
|---|---|---|
| **Tandem Repeats Finder (TRF)** | Free for academic use; see upstream terms | https://github.com/Benson-Genomics-Lab/TRF |
| **HipSTR** | GPL v2 | https://github.com/HipSTR-Tool/HipSTR |
| **BEDTools** | MIT | https://github.com/arq5x/bedtools2 |
| **pyfaidx** (`faidx`) | BSD-3-Clause | https://github.com/mdshw5/pyfaidx |
| **R** and packages `tidyr`, `vcfR`, `data.table` | GPL-2/GPL-3 / MPL-2.0 | https://cran.r-project.org |

pSTRminer invokes TRF and the R packages as separate programs and does not link
against or redistribute them.

**Note on HipSTR.** pSTRminer does not bundle, link against, or redistribute any
part of HipSTR. HipSTR is run independently by the user to generate the VCF that
Stage 2 consumes. The call-level filtering step in Stage 2 is performed by
`scripts/pstr_filter_vcf.py`, an original implementation written for pSTRminer
and covered by the MIT License in `LICENSE`; it is not derived from HipSTR's
source code and carries no dependency on it.
