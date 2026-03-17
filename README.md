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

## Build AnchorWave (submodule)

Build the `AnchorWave` binary from the included submodule:

```bash
cd AnchorWave
cmake ./
make -j
cd ..
```

The alignment script will use `anchorwave` from your `PATH` if available, or fall back to the local binary under `AnchorWave/`.

## Files

v2 and v5 maize genome files, from [maizegdb](https://download.maizegdb.org/Zm-B73-REFERENCE-NAM-5.0/):

- `v2.fa.gz`
- `v5.fa.gz`

You also need a **reference annotation file** (`.gff3` or `.gtf`) matching the reference genome used with `--ref`.

- `v5.gff.gz`

Scripts:

- `scripts/align_with_anchorwave.sh`

## Requirements

Run `module load minimap2` (or install `minimap2` so it is available on `PATH`).

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

Typical run from repository root after building AnchorWave:

```bash
scripts/align_with_anchorwave.sh \
  --gff v5.gff3.gz \
  --ref v5.fa.gz \
  --query v2.fa.gz \
  --threads 16 \
  --outdir anchorwave_out
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
