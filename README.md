# Mappy: 

## Clone With Submodule

Clone this repository and initialize `AnchorWave/` in one step:

```bash
git clone --recurse-submodules <repo-url>
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

## Files

v2 and v5 maize genome files, from [maizegdb](https://download.maizegdb.org/Zm-B73-REFERENCE-NAM-5.0/):

- `v2.fa.gz`
- `v5.fa.gz`
- `v2.gff.gz`
- `v5.gff.gz`

Scripts:

- `scripts/align_with_anchorwave.sh`

## Requirements

Run `module load minimap2`
Install and make available on `PATH`:

- `anchorwave`

You also need a **reference annotation file** (`.gff3` or `.gtf`) matching the reference genome used with `--ref`.

## Quick Start

Run with explicit inputs:

```bash
scripts/align_with_anchorwave.sh \
  --gff path/to/reference.gff3 \
  --ref B73_RefGen_v2.fa.gz \
  --query Zm-B73-REFERENCE-NAM-5.0.fa.gz \
  --threads 16 \
  --outdir anchorwave_out
```

Or let the script auto-detect exactly two FASTA files in the current directory:

```bash
scripts/align_with_anchorwave.sh --gff path/to/reference.gff3 --threads 16
```

## Output

By default (`--outdir anchorwave_out`):

- `anchorwave_out/alignment.maf`
- `anchorwave_out/alignment.fragments.maf`
- `anchorwave_out/anchors.txt`
- `anchorwave_out/anchorwave.log`

## Notes for Maize-Scale Genomes

- Start with `--threads 16` (or higher based on available CPU).
- Use SSD-backed storage for faster SAM/MAF I/O.
- Keep sufficient free disk space: intermediate and final alignment files can be large.
- Default mode is `proali`; switch to `genoali` with `--mode genoali` if needed.

## Script Help

```bash
scripts/align_with_anchorwave.sh --help
```
