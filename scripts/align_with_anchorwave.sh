#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/align_with_anchorwave.sh --gff <reference.gff3|gtf> [options]

Required:
  --gff PATH            Reference annotation file (GFF3/GTF) for the reference genome.

Optional:
  --ref PATH            Reference genome FASTA(.gz). If omitted, auto-detects from repo root.
  --query PATH          Query genome FASTA(.gz). If omitted, auto-detects from repo root.
  --mode MODE           AnchorWave mode: proali or genoali (default: proali).
  --outdir DIR          Output directory (default: anchorwave_out).
  --threads INT         Thread count for minimap2 (default: 8).
  --R INT               proali reference polyploidy level (default: 1).
  --Q INT               proali query polyploidy level (default: 1).
  --iv                  For genoali, include -IV.
  -h, --help            Show this help.

Notes:
  - If --ref/--query are not provided, the script expects exactly two FASTA files
    in the current directory matching:
      *.fa, *.fasta, *.fna, *.fa.gz, *.fasta.gz, *.fna.gz
  - Compressed FASTA inputs are decompressed into a temporary directory in /tmp.
  - AnchorWave is resolved in this order:
      1) anchorwave on PATH
      2) local binary under ./AnchorWave (submodule checkout/build output)
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command not found: $1" >&2
    exit 1
  fi
}

realpath_safe() {
  local p="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$p"
  else
    python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$p"
  fi
}

resolve_anchorwave_bin() {
  if command -v anchorwave >/dev/null 2>&1; then
    command -v anchorwave
    return 0
  fi

  local candidates=(
    "$REPO_ROOT/AnchorWave/anchorwave"
    "$REPO_ROOT/AnchorWave/anchorwave_sse4.1"
    "$REPO_ROOT/AnchorWave/anchorwave_avx2"
    "$REPO_ROOT/AnchorWave/anchorwave_avx512"
    "$REPO_ROOT/AnchorWave/anchorwave_sse2"
    "$REPO_ROOT/AnchorWave/anchorwave_arm"
    "$REPO_ROOT/AnchorWave/build/anchorwave"
    "$REPO_ROOT/AnchorWave/build/anchorwave_sse4.1"
    "$REPO_ROOT/AnchorWave/build/anchorwave_avx2"
    "$REPO_ROOT/AnchorWave/build/anchorwave_avx512"
    "$REPO_ROOT/AnchorWave/build/anchorwave_sse2"
    "$REPO_ROOT/AnchorWave/build/anchorwave_arm"
  )
  local c=""
  for c in "${candidates[@]}"; do
    if [[ -x "$c" ]]; then
      echo "$c"
      return 0
    fi
  done

  echo "ERROR: Required command not found: anchorwave" >&2
  echo "Searched PATH and local candidates under $REPO_ROOT/AnchorWave." >&2
  echo "Build AnchorWave first, e.g.: (cd AnchorWave && cmake ./ && make -j)" >&2
  return 1
}

prepare_fasta() {
  local input="$1"
  local outvar="$2"
  local abs_input
  abs_input="$(realpath_safe "$input")"

  if [[ "$abs_input" == *.gz ]]; then
    local base
    base="$(basename "$abs_input" .gz)"
    local out="$TMPDIR_MAPPY/$base"
    echo "Decompressing $abs_input -> $out" >&2
    gunzip -c "$abs_input" > "$out"
    printf -v "$outvar" '%s' "$out"
  else
    printf -v "$outvar" '%s' "$abs_input"
  fi
}

gff=""
ref=""
query=""
mode="proali"
outdir="anchorwave_out"
threads=8
R=1
Q=1
use_iv=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gff)
      gff="${2:-}"
      shift 2
      ;;
    --ref)
      ref="${2:-}"
      shift 2
      ;;
    --query)
      query="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --outdir)
      outdir="${2:-}"
      shift 2
      ;;
    --threads)
      threads="${2:-}"
      shift 2
      ;;
    --R)
      R="${2:-}"
      shift 2
      ;;
    --Q)
      Q="${2:-}"
      shift 2
      ;;
    --iv)
      use_iv=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$gff" ]]; then
  echo "ERROR: --gff is required." >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$gff" ]]; then
  echo "ERROR: GFF/GTF not found: $gff" >&2
  exit 1
fi

shopt -s nocasematch
if [[ "$mode" != "proali" && "$mode" != "genoali" ]]; then
  echo "ERROR: --mode must be proali or genoali." >&2
  exit 1
fi
shopt -u nocasematch

if [[ -z "$ref" || -z "$query" ]]; then
  mapfile -t fasta_files < <(
    find . -maxdepth 1 -type f \
      \( -name "*.fa" -o -name "*.fasta" -o -name "*.fna" -o -name "*.fa.gz" -o -name "*.fasta.gz" -o -name "*.fna.gz" \) \
      | sort
  )
  if [[ "${#fasta_files[@]}" -ne 2 ]]; then
    echo "ERROR: Could not auto-detect exactly two FASTA files in current directory." >&2
    echo "Found ${#fasta_files[@]} candidate(s):" >&2
    printf '  %s\n' "${fasta_files[@]}" >&2
    echo "Provide explicit --ref and --query." >&2
    exit 1
  fi
  ref="${fasta_files[0]}"
  query="${fasta_files[1]}"
fi

if [[ ! -f "$ref" ]]; then
  echo "ERROR: Reference FASTA not found: $ref" >&2
  exit 1
fi
if [[ ! -f "$query" ]]; then
  echo "ERROR: Query FASTA not found: $query" >&2
  exit 1
fi

require_cmd minimap2
require_cmd gunzip
anchorwave_bin="$(resolve_anchorwave_bin)"

mkdir -p "$outdir"

TMPDIR_MAPPY="$(mktemp -d /tmp/mappy-anchorwave-XXXXXX)"
trap 'rm -rf "$TMPDIR_MAPPY"' EXIT

gff_abs="$(realpath_safe "$gff")"
outdir_abs="$(realpath_safe "$outdir")"

prepare_fasta "$ref" ref_fasta
prepare_fasta "$query" query_fasta

cds_fa="$outdir_abs/cds.fa"
ref_sam="$outdir_abs/ref.sam"
query_sam="$outdir_abs/query.sam"
anchors="$outdir_abs/anchors.txt"
maf="$outdir_abs/alignment.maf"
frag_maf="$outdir_abs/alignment.fragments.maf"
log="$outdir_abs/anchorwave.log"

echo "Reference FASTA: $ref_fasta"
echo "Query FASTA:     $query_fasta"
echo "GFF/GTF:         $gff_abs"
echo "Mode:            $mode"
echo "Output dir:      $outdir_abs"
echo "AnchorWave:      $anchorwave_bin"

echo "[1/4] Extracting CDS with anchorwave gff2seq"
"$anchorwave_bin" gff2seq -i "$gff_abs" -r "$ref_fasta" -o "$cds_fa"

echo "[2/4] Lifting CDS to reference with minimap2"
minimap2 -x splice -t "$threads" -k 12 -a -p 0.4 -N 20 "$ref_fasta" "$cds_fa" > "$ref_sam"

echo "[3/4] Lifting CDS to query with minimap2"
minimap2 -x splice -t "$threads" -k 12 -a -p 0.4 -N 20 "$query_fasta" "$cds_fa" > "$query_sam"

echo "[4/4] Running AnchorWave $mode"
if [[ "$mode" == "proali" ]]; then
  "$anchorwave_bin" proali \
    -i "$gff_abs" \
    -as "$cds_fa" \
    -r "$ref_fasta" \
    -a "$query_sam" \
    -ar "$ref_sam" \
    -s "$query_fasta" \
    -n "$anchors" \
    -R "$R" \
    -Q "$Q" \
    -o "$maf" \
    -f "$frag_maf" \
    > "$log" 2>&1
else
  iv_flag=()
  if [[ "$use_iv" -eq 1 ]]; then
    iv_flag=(-IV)
  fi
  "$anchorwave_bin" genoAli \
    -i "$gff_abs" \
    -as "$cds_fa" \
    -r "$ref_fasta" \
    -a "$query_sam" \
    -ar "$ref_sam" \
    -s "$query_fasta" \
    -n "$anchors" \
    -o "$maf" \
    -f "$frag_maf" \
    "${iv_flag[@]}" \
    > "$log" 2>&1
fi

echo "Done."
echo "MAF:            $maf"
echo "Fragment MAF:   $frag_maf"
echo "Anchors:        $anchors"
echo "Log:            $log"
