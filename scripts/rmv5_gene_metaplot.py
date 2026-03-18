#!/usr/bin/env python3
"""Plot strand-aware cM/Mb metaplots around gene starts and stops.

This script uses a piecewise-constant recombination track from RMv5.bed and
gene models from a GFF3 file. It produces a single plot with two overlaid
profiles:

1. TSS-aligned metaplot: upstream flank and the first bases after the TSS.
2. TTS-aligned metaplot: the last bases before the stop codon and the
   downstream flank.

All coordinates are handled in transcript orientation, so minus-strand genes
are reversed before binning.
"""

from __future__ import annotations

import argparse
import bisect
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot cM/Mb metaplots around gene starts and stops."
    )
    parser.add_argument("--rmv5-bed", default="RMv5.bed", help="RMv5 BED/bed-like track")
    parser.add_argument("--gff3", default="v5.gff3", help="Genome annotation GFF3")
    parser.add_argument("--output", default="RMv5_gene_metaplot.png", help="Output PNG")
    parser.add_argument("--window-size", type=int, default=100, help="Bin size in bp (default: 100)")
    parser.add_argument("--upstream", type=int, default=5000, help="TSS upstream flank in bp (default: 5000)")
    parser.add_argument("--downstream", type=int, default=5000, help="TTS downstream flank in bp (default: 5000)")
    parser.add_argument("--tss-window", type=int, default=500, help="Bases after TSS to include (default: 500)")
    parser.add_argument("--tts-window", type=int, default=500, help="Bases before TTS to include (default: 500)")
    parser.add_argument(
        "--min-gene-length",
        type=int,
        default=0,
        help="Skip genes shorter than this many bp (default: 0)",
    )
    return parser.parse_args()


def normalize_chrom(chrom: str) -> str:
    if chrom.startswith("chr") and chrom[3:].isdigit():
        return "Chr" + chrom[3:]
    if chrom.startswith("Chr") and chrom[3:].isdigit():
        return chrom
    return chrom


def load_track(
    path: Path,
) -> tuple[dict[str, list[tuple[int, int, float]]], dict[str, list[int]], dict[str, int]]:
    """Load RMv5.bed as closed intervals per chromosome."""
    track: dict[str, list[tuple[int, int, float]]] = defaultdict(list)
    starts: dict[str, list[int]] = defaultdict(list)
    chrom_max: dict[str, int] = defaultdict(int)
    with path.open() as fh:
        header = next(fh, None)
        for line in fh:
            if not line.strip():
                continue
            chrom, start_s, end_s, *_rest = line.rstrip("\n").split("\t")
            start = int(start_s)
            end = int(end_s)
            value = float(line.rstrip("\n").split("\t")[5])
            track[chrom].append((start, end, value))
            starts[chrom].append(start)
            chrom_max[chrom] = max(chrom_max[chrom], end)
    for chrom in track:
        track[chrom].sort()
        starts[chrom].sort()
    return track, starts, chrom_max


def load_genes(path: Path, keep_chroms: set[str]) -> list[tuple[str, int, int, str]]:
    """Load gene features, returning 0-based closed coordinates."""
    genes: list[tuple[str, int, int, str]] = []
    with path.open() as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            chrom, _source, feature, start_s, end_s, _score, strand, _phase, _attrs = line.rstrip("\n").split("\t")
            if feature != "gene":
                continue
            chrom = normalize_chrom(chrom)
            if chrom not in keep_chroms:
                continue
            start = int(start_s) - 1
            end = int(end_s) - 1
            genes.append((chrom, start, end, strand))
    return genes


def query_mean(
    track: list[tuple[int, int, float]],
    starts: list[int],
    start: int,
    end: int,
) -> float | None:
    """Return mean cM/Mb over a closed interval, treating uncovered bases as zero."""
    if end < start:
        return None
    if not track:
        return 0.0

    idx = bisect.bisect_right(starts, start) - 1
    if idx < 0:
        idx = 0

    total = 0.0
    span = end - start + 1
    while idx < len(track) and track[idx][0] <= end:
        seg_start, seg_end, value = track[idx]
        overlap_start = max(start, seg_start)
        overlap_end = min(end, seg_end)
        if overlap_end >= overlap_start:
            total += value * (overlap_end - overlap_start + 1)
        idx += 1
    return total / span


def oriented_interval(anchor: int, strand: str, rel_start: int, rel_end: int) -> tuple[int, int]:
    """Map a transcript-oriented interval to genomic closed coordinates."""
    if strand == "+":
        return anchor + rel_start, anchor + rel_end
    # minus-strand genes run in reverse genomic direction.
    return anchor - rel_end, anchor - rel_start


def panel_bins(total_up: int, total_down: int, window: int) -> list[tuple[int, int, float]]:
    """Return transcript-oriented bins as (rel_start, rel_end, center)."""
    bins: list[tuple[int, int, float]] = []
    rel_start = -total_up
    rel_end = total_down
    pos = rel_start
    while pos < rel_end:
        bin_start = pos
        bin_end = min(pos + window - 1, rel_end - 1)
        bins.append((bin_start, bin_end, (bin_start + bin_end) / 2.0))
        pos = bin_end + 1
    return bins


def accumulate_panel(
    genes: list[tuple[str, int, int, str]],
    track: dict[str, list[tuple[int, int, float]]],
    starts: dict[str, list[int]],
    chrom_max: dict[str, int],
    window: int,
    upstream: int,
    downstream: int,
    tss_side: str,
) -> tuple[list[float], list[float], list[int], list[float]]:
    """Accumulate mean cM/Mb per bin across all genes."""
    bins = panel_bins(upstream, downstream, window)
    sums = [0.0 for _ in bins]
    counts = [0 for _ in bins]
    centers = [center for _s, _e, center in bins]

    for chrom, start, end, strand in genes:
        if chrom not in track:
            continue
        gene_len = end - start + 1
        if gene_len < 1:
            continue

        if tss_side == "tss":
            anchor = start if strand == "+" else end
        else:
            anchor = end if strand == "+" else start

        chr_limit = chrom_max.get(chrom, -1)
        for i, (rel_start, rel_end, _center) in enumerate(bins):
            g_start, g_end = oriented_interval(anchor, strand, rel_start, rel_end)
            g_start = max(0, g_start)
            g_end = min(chr_limit, g_end)
            if g_end < g_start:
                continue
            mean_val = query_mean(track[chrom], starts[chrom], g_start, g_end)
            if mean_val is None:
                continue
            sums[i] += mean_val
            counts[i] += 1

    averages = [s / c if c else float("nan") for s, c in zip(sums, counts)]
    return centers, averages, counts, [bin_end - bin_start + 1 for bin_start, bin_end, _center in bins]


def plot_series(ax, centers, values, label, color):
    ax.plot(centers, values, color=color, linewidth=1.8, label=label)


def style_plot(ax, title, xlabel, window, x_limits, tss_join, tts_join):
    ax.axvline(0, color="#333333", linewidth=0.8, alpha=0.8)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Average cM/Mb")
    ax.grid(color="#d9d9d9", linewidth=0.5, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(*x_limits)
    tick_step = max(window * 10, 500)
    tick_start = int(math.floor(x_limits[0] / tick_step) * tick_step)
    tick_end = int(math.ceil(x_limits[1] / tick_step) * tick_step)
    ticks = list(range(tick_start, tick_end + tick_step, tick_step))
    ticks = sorted(set(ticks + [tss_join, tts_join]))
    labels = []
    for tick in ticks:
        if tick == tss_join:
            labels.append("TSS")
        elif tick == tts_join:
            labels.append("TTS")
        else:
            labels.append(str(int(tick)))
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.legend(frameon=False)


def main() -> None:
    args = parse_args()
    rm_path = Path(args.rmv5_bed)
    gff_path = Path(args.gff3)
    out_path = Path(args.output)

    track, starts, chrom_max = load_track(rm_path)
    genes = load_genes(gff_path, set(track))
    if args.min_gene_length > 0:
        genes = [g for g in genes if (g[2] - g[1] + 1) >= args.min_gene_length]

    tss_centers, tss_values, tss_counts, _ = accumulate_panel(
        genes,
        track,
        starts,
        chrom_max,
        args.window_size,
        args.upstream,
        args.tss_window,
        "tss",
    )
    tts_centers, tts_values, tts_counts, _ = accumulate_panel(
        genes,
        track,
        starts,
        chrom_max,
        args.window_size,
        args.tts_window,
        args.downstream,
        "tts",
    )

    tss_plot_centers = [center - args.tss_window for center in tss_centers]
    tts_plot_centers = [center + args.tts_window for center in tts_centers]

    fig, ax = plt.subplots(figsize=(12, 5.5))
    plot_series(
        ax,
        tss_plot_centers,
        tss_values,
        f"TSS: {args.upstream} bp upstream to {args.tss_window} bp after TSS",
        "#1f5a91",
    )
    plot_series(
        ax,
        tts_plot_centers,
        tts_values,
        f"TTS: {args.tts_window} bp before stop to {args.downstream} bp downstream",
        "#c45a1a",
    )
    x_min = tss_plot_centers[0] if tss_plot_centers else 0
    x_max = tts_plot_centers[-1] if tts_plot_centers else 0
    style_plot(
        ax,
        "Gene metaplot around TSS and TTS",
        "Distance from gene boundary (center joins TSS and TTS windows)",
        args.window_size,
        (x_min, x_max),
        -args.tss_window,
        args.tts_window,
    )
    fig.suptitle(
        f"RMv5 cM/Mb metaplot across {len(genes)} genes",
        fontsize=15,
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=250)


if __name__ == "__main__":
    main()
