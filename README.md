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

## OGUT Marker Map Provenance

The OGUT marker map in this repository traces back to the marker resource reported in:

- Ogut F, Bian Y, Bradbury PJ, Holland JB. 2015. *Joint-multiple family linkage analysis predicts within-family variation better than single-family analysis of the maize nested association mapping population*. Heredity. [https://doi.org/10.1038/hdy.2014.123](https://doi.org/10.1038/hdy.2014.123)

The original marker table was recorded here as `ogut_fifthcM_map_agpv2.csv`, then converted to BED format as `ogut_fifthcM_map_agpv2.bed`. The BED conversion uses chromosome, physical position, marker name, source SNP ID, and cM value, with 0-based half-open coordinates:

```bash
awk -F',' 'NR>1 { pos=$4+0; print $3 "\t" pos-1 "\t" pos "\t" $2 "\t" $1 "\t" $5 }' \
  ogut_fifthcM_map_agpv2.csv > ogut_fifthcM_map_agpv2.bed
```

## Lift-Over to B73 v5

To move marker coordinates from AGPv2 to B73 v5, we aligned the v2 and v5 maize genome assemblies using AnchorWave, then converted the resulting MAF alignment into a UCSC chain file with [maf-convert](https://gitlab.com/mcfrith/last/-/blob/main/doc/maf-convert.rst):

```bash
maf-convert chain AW_out/alignment.maf > v2v5.chain
```

After building the chain file, the marker BED was translated to v5 coordinates with [CrossMap](https://github.com/liguowang/CrossMap):

```bash
CrossMap bed v2v5.chain ogut_fifthcM_map_agpv2.bed ogut_v5.bed
```

This produced `ogut_v5.bed`, which contains the lifted marker positions on the v5 assembly while preserving the marker IDs and cM annotations.

## Post-Lift Manual Marker Adjustments

After inspecting `ogut_v5.bed`, we found markers whose physical coordinates were not monotonically increasing within chromosome even though the cM values remained monotonic. To keep the map order consistent with the physical order on v5, we adjusted the cM values for the affected markers without changing their lifted physical positions.

Applied adjustments:

- On `Chr3`, `M2179` and `M2180` kept their physical coordinates, but their cM values were swapped.
- On `Chr7`, the block from `M5158` through `M5171` kept its physical coordinates, and the cM values across that block were reversed so that genetic order matches the physical order.

The pre-edit `ogut_v5.bed` was committed as `ce1ab1f`, and a local backup copy was also written to `ogut_v5.bed.bak` before those edits.

## Requirements

Run `module load last` and `module load minimap2` (or install both tools so they are available on `PATH`).

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
