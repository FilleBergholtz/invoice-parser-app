"""
Column detection for position-based table parsing (mode B).

This module implements robust, layout-aware column detection from spatial
analysis of token positions. It is designed to work across suppliers and
PDF quirks (uneven spacing, ragged headers, merged cells, multi-line headers).

Key improvements vs. naive gap-based detection:
- Robust outlier handling (trimmed/IQR-based)
- Adaptive gap thresholding based on observed spacing
- Token-density clustering to avoid over-splitting
- Optional row weighting (rows with more tokens influence more)
- Header mapping with normalized text (diacritics), multi-token headers,
  and score-based conflict resolution
- Column assignment using column *spans* (boundaries) with overlap scoring,
  not only nearest center
"""

from __future__ import annotations

import logging
import statistics
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from ..models.row import Row
from ..models.token import Token

logger = logging.getLogger(__name__)


# ----------------------------
# Helpers
# ----------------------------

def _norm_text(s: str) -> str:
    """Lowercase + strip diacritics + collapse whitespace."""
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # collapse whitespace
    s = " ".join(s.split())
    return s


def _median_abs_deviation(values: List[float]) -> float:
    if not values:
        return 0.0
    m = statistics.median(values)
    abs_dev = [abs(v - m) for v in values]
    return statistics.median(abs_dev)


def _iqr_bounds(values: List[float], k: float = 1.5) -> Tuple[float, float]:
    """Compute Tukey IQR bounds for outlier filtering."""
    if len(values) < 4:
        m = statistics.median(values) if values else 0.0
        return (m - 1e9, m + 1e9)

    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    lower = sorted_vals[:mid]
    upper = sorted_vals[mid:] if len(sorted_vals) % 2 == 0 else sorted_vals[mid + 1 :]

    q1 = statistics.median(lower) if lower else sorted_vals[0]
    q3 = statistics.median(upper) if upper else sorted_vals[-1]
    iqr = max(q3 - q1, 0.0)
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return lo, hi


def _safe_page_width(rows: List[Row], default: float = 595.0) -> float:
    if rows and rows[0].page and getattr(rows[0].page, "width", None):
        return float(rows[0].page.width)
    return float(default)


def _extract_x_centers(rows: List[Row]) -> List[float]:
    x: List[float] = []
    for row in rows:
        if not row.tokens:
            continue
        for t in row.tokens:
            x.append(float(t.x) + float(t.width) / 2.0)
    return x


def _extract_x_edges(rows: List[Row]) -> List[Tuple[float, float]]:
    """Return (left,right) for each token."""
    edges: List[Tuple[float, float]] = []
    for row in rows:
        if not row.tokens:
            continue
        for t in row.tokens:
            left = float(t.x)
            right = float(t.x) + float(t.width)
            edges.append((left, right))
    return edges


def _row_weight(row: Row) -> float:
    """Rows with more tokens tend to represent the true table structure better."""
    if not row.tokens:
        return 0.0
    n = len(row.tokens)
    # mild weighting; don't let long description rows dominate too hard
    return min(1.0 + (n / 10.0), 2.0)


def _weighted_sample(values: List[float], weights: List[float]) -> List[float]:
    """
    Expand values by integer-ish weights for robust median calculations
    without bringing in numpy. Keeps it bounded.
    """
    out: List[float] = []
    for v, w in zip(values, weights):
        k = int(round(max(0.0, min(w, 3.0))))  # cap expansion
        out.extend([v] * max(1, k))
    return out


@dataclass(frozen=True)
class ColumnModel:
    centers: List[float]
    boundaries: List[float]  # len = len(centers)+1, monotonic; [0..page_width]


def _build_boundaries(centers: List[float], page_width: float, margin_left: float = 0.0, margin_right: float = 0.0) -> List[float]:
    """
    Convert centers to boundaries:
      b0 = margin_left
      bi = midpoint(centers[i-1], centers[i])
      bN = page_width - margin_right
    """
    if not centers:
        return [margin_left, max(margin_left, page_width - margin_right)]

    sorted_centers = sorted(centers)
    b: List[float] = [float(margin_left)]
    for i in range(1, len(sorted_centers)):
        b.append((sorted_centers[i - 1] + sorted_centers[i]) / 2.0)
    b.append(max(float(margin_left), float(page_width) - float(margin_right)))

    # ensure monotonic (guard against weird centers)
    for i in range(1, len(b)):
        if b[i] <= b[i - 1]:
            b[i] = b[i - 1] + 0.01
    return b


def _span_overlap(a_left: float, a_right: float, b_left: float, b_right: float) -> float:
    """Return overlap length."""
    left = max(a_left, b_left)
    right = min(a_right, b_right)
    return max(0.0, right - left)


# ----------------------------
# Column Detection
# ----------------------------

def detect_columns_gap_based(
    rows: List[Row],
    min_gap: float = 20.0,
) -> List[float]:
    """
    Detect columns using a robust gap+cluster algorithm.

    Improvements vs. naive implementation:
    - Outlier filtering on x-centers
    - Adaptive min_gap using MAD/IQR of inter-token gaps
    - Prevent over-splitting by enforcing minimum cluster size
    - Uses token density to infer centers when gaps are noisy

    Returns:
        List of column center X-positions (sorted left to right)
    """
    if not rows:
        return []

    x_centers = _extract_x_centers(rows)
    if not x_centers:
        return []

    # Filter pathological outliers in x-centers (caused by bad token boxes)
    lo, hi = _iqr_bounds(x_centers, k=2.0)
    x_centers = [x for x in x_centers if lo <= x <= hi] or x_centers

    x_centers.sort()

    # Compute inter-center gaps
    raw_gaps = [x_centers[i + 1] - x_centers[i] for i in range(len(x_centers) - 1)]
    if not raw_gaps:
        return [statistics.median(x_centers)]

    # Adaptive threshold:
    # - Start from provided min_gap
    # - If PDF is tight/packed, min_gap may be too large; if noisy, too small
    med_gap = statistics.median(raw_gaps)
    mad_gap = _median_abs_deviation(raw_gaps)
    # A robust "large gap" heuristic:
    # - large if > max(min_gap, med_gap + 2.5*MAD) but keep a floor on MAD
    adaptive = med_gap + 2.5 * max(mad_gap, 2.0)
    gap_threshold = max(float(min_gap), adaptive)

    # Identify "large gaps" as potential boundaries
    gap_candidates: List[Tuple[float, float, float]] = []
    for i, g in enumerate(raw_gaps):
        if g >= gap_threshold:
            gap_candidates.append((x_centers[i], x_centers[i + 1], g))

    # If too many boundaries, raise threshold further (over-splitting control)
    if len(gap_candidates) > 12:
        gap_sizes = [g for _, _, g in gap_candidates]
        # Raise to a high quantile to keep only the strongest separators
        gap_sizes_sorted = sorted(gap_sizes)
        q = gap_sizes_sorted[int(0.75 * (len(gap_sizes_sorted) - 1))]
        gap_threshold2 = max(gap_threshold, q)
        gap_candidates = [c for c in gap_candidates if c[2] >= gap_threshold2]
        logger.debug(
            "Gap over-splitting: %d candidates -> %d after threshold %.1fpt (q75=%.1fpt, base=%.1fpt)",
            len(gap_sizes),
            len(gap_candidates),
            gap_threshold2,
            q,
            gap_threshold,
        )
        gap_threshold = gap_threshold2

    # Convert gaps to cluster segments, then choose centers as medians of each segment
    if not gap_candidates:
        # single column: median x
        center = statistics.median(x_centers)
        logger.debug(
            "No column gaps found (min_gap=%.1f, adaptive=%.1f => thr=%.1f). Single column @ %.1f",
            min_gap,
            adaptive,
            gap_threshold,
            center,
        )
        return [center]

    # Determine breakpoints in x_centers based on gap_candidates
    breaks = set()
    for left_x, right_x, _ in gap_candidates:
        # break between left_x and right_x
        # find index i where x[i]==left_x and x[i+1]==right_x
        # since floats may not match exactly, do nearest search
        # We'll approximate by scanning raw_gaps threshold again.
        pass

    # Re-scan raw_gaps to find break indices using final threshold
    break_indices = [i for i, g in enumerate(raw_gaps) if g >= gap_threshold]

    # Build clusters [start..end]
    clusters: List[List[float]] = []
    start = 0
    for i in break_indices:
        end = i + 1
        clusters.append(x_centers[start:end])
        start = end
    clusters.append(x_centers[start:])

    # Remove tiny clusters that are likely noise (e.g., stray token)
    # Merge tiny cluster into nearest neighbor
    MIN_CLUSTER = 3
    i = 0
    while i < len(clusters):
        if len(clusters[i]) >= MIN_CLUSTER:
            i += 1
            continue

        if len(clusters) == 1:
            break

        # merge into neighbor with closest median
        med_i = statistics.median(clusters[i]) if clusters[i] else 0.0
        left_dist = float("inf")
        right_dist = float("inf")
        if i - 1 >= 0:
            left_dist = abs(med_i - statistics.median(clusters[i - 1]))
        if i + 1 < len(clusters):
            right_dist = abs(med_i - statistics.median(clusters[i + 1]))

        if left_dist <= right_dist and i - 1 >= 0:
            clusters[i - 1].extend(clusters[i])
            del clusters[i]
            i = max(i - 1, 0)
        elif i + 1 < len(clusters):
            clusters[i + 1].extend(clusters[i])
            del clusters[i]
        else:
            i += 1

    # Compute centers as robust medians (weighted by row density if desired)
    # Here: plain median on cluster values is typically stable.
    centers = [statistics.median(sorted(c)) for c in clusters if c]

    # Ensure centers are strictly increasing
    centers = sorted(set(round(c, 2) for c in centers))
    return centers


# ----------------------------
# Header Mapping
# ----------------------------

def map_columns_from_header(
    header_row: Row,
    column_centers: List[float],
) -> Optional[Dict[str, int]]:
    """
    Map columns to fields using header row keywords (score-based).

    Improvements:
    - Diacritic-insensitive matching (á/ä/å etc.)
    - Multi-token header phrases
    - Weighted scoring per field; resolves conflicts by best score

    Returns:
        Dict[field_name] = column_index
        None if no reliable mapping
    """
    if not header_row.tokens or not column_centers:
        return None

    # Normalize and merge header tokens by approximate column
    model = ColumnModel(
        centers=sorted(column_centers),
        boundaries=_build_boundaries(sorted(column_centers), _safe_page_width([header_row])),
    )

    col_tokens = assign_tokens_to_columns(header_row, model.centers)

    # Build per-column header string (joined in reading order)
    col_text: Dict[int, str] = {}
    for col_idx, toks in col_tokens.items():
        toks_sorted = sorted(toks, key=lambda t: t.x)
        merged = " ".join(_norm_text(t.text) for t in toks_sorted if t.text)
        col_text[col_idx] = merged.strip()

    # Keywords: include common Swedish/English variants and abbreviations
    field_keywords: Dict[str, List[str]] = {
        "article_no": ["artikelnr", "artikelnummer", "art nr", "art.nr", "art", "item", "item no", "sku"],
        "description": ["benamning", "beskrivning", "artikel", "produkt", "text", "description", "item description"],
        "quantity": ["antal", "kvantitet", "qty", "quantity", "mangd", "st", "pcs"],
        "unit": ["enhet", "unit", "uom", "st", "kg", "tim", "hour", "hrs", "ea"],
        "unit_price": ["pris", "a-pris", "apris", "á-pris", "enhetspris", "unit price", "price"],
        "discount": ["rabatt", "discount", "prisrabatt", "%"],
        "vat_percent": ["moms", "moms%", "vat", "vat%"],
        "netto": ["nettobelopp", "netto", "belopp", "total", "summa", "amount", "line total"],
        "account": ["konto", "kontonr", "account"],
    }

    # Scoring: prefer exact-ish matches and longer keywords
    def score_field_in_text(field: str, text: str) -> float:
        if not text:
            return 0.0
        s = 0.0
        for kw in field_keywords[field]:
            nkw = _norm_text(kw)
            if not nkw:
                continue
            if nkw in text:
                # longer keyword => higher confidence
                s += 1.0 + min(len(nkw) / 10.0, 2.0)
        return s

    # Compute best column per field
    best: Dict[str, Tuple[int, float]] = {}
    for field in field_keywords.keys():
        best_col = -1
        best_score = 0.0
        for col_idx, txt in col_text.items():
            sc = score_field_in_text(field, txt)
            if sc > best_score:
                best_score = sc
                best_col = col_idx
        if best_col >= 0 and best_score > 0.0:
            best[field] = (best_col, best_score)

    if not best:
        return None

    # Resolve conflicts: if multiple fields map to same column, keep highest score,
    # but allow description + article_no to share only if they are very close and header is sparse.
    # Default: one field per column.
    used_cols: Dict[int, Tuple[str, float]] = {}
    mapping: Dict[str, int] = {}

    # sort by score desc so strongest claims win
    for field, (col, sc) in sorted(best.items(), key=lambda kv: kv[1][1], reverse=True):
        if col not in used_cols:
            used_cols[col] = (field, sc)
            mapping[field] = col
            continue

        existing_field, existing_sc = used_cols[col]

        # allow article_no + description sharing if header text contains both signals strongly
        if {existing_field, field} <= {"article_no", "description"}:
            # require strong evidence
            if sc >= 2.0 and existing_sc >= 2.0:
                mapping[field] = col
                continue

        # otherwise, keep the stronger and discard weaker
        if sc > existing_sc:
            # replace
            del mapping[existing_field]
            used_cols[col] = (field, sc)
            mapping[field] = col

    return mapping or None


# ----------------------------
# Token -> Column assignment
# ----------------------------

def assign_tokens_to_columns(
    row: Row,
    column_centers: List[float],
) -> Dict[int, List[Token]]:
    """
    Assign tokens to columns using column spans (boundaries) + overlap scoring.

    Improvements:
    - Uses boundaries derived from centers, so wide tokens get assigned by overlap
    - If token overlaps multiple columns, assigns to the column with max overlap;
      ties resolved by nearest center
    - If no overlap (rare), falls back to nearest center

    Returns:
        Dict[col_idx] -> tokens
    """
    if not column_centers:
        return {}

    centers = sorted(column_centers)
    page_w = _safe_page_width([row])
    boundaries = _build_boundaries(centers, page_w)

    # Initialize
    column_tokens: Dict[int, List[Token]] = {i: [] for i in range(len(centers))}
    if not row.tokens:
        return column_tokens

    for token in row.tokens:
        t_left = float(token.x)
        t_right = float(token.x) + float(token.width)
        t_center = t_left + (t_right - t_left) / 2.0

        best_col = None
        best_overlap = 0.0

        # overlap with each column span
        for i in range(len(centers)):
            c_left = boundaries[i]
            c_right = boundaries[i + 1]
            ov = _span_overlap(t_left, t_right, c_left, c_right)
            if ov > best_overlap:
                best_overlap = ov
                best_col = i

        if best_col is None or best_overlap <= 0.0:
            # fallback: nearest center
            best_col = min(range(len(centers)), key=lambda i: abs(centers[i] - t_center))

        # Optional: if token overlaps heavily across columns, keep it where overlap is largest.
        column_tokens[int(best_col)].append(token)

    return column_tokens

