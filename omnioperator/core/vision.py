"""Vision module: screen grabber, grid-overlay coordinate mapper and OCR /
element visual grounding for OmniOperator.

All operations operate on the pixel-grid representation exposed by the
SimulatedOS environment (an ASCII framebuffer). Real production deployments
swap `screen_grab` for `PIL.ImageGrab.grab()` and `ground_element` for a
TrOCR / PaddleOCR / SAM-based pipeline — the interface stays identical.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GroundedElement:
    """Result of grounding a natural-language reference to pixel coords."""
    query: str
    bbox: Tuple[int, int, int, int]  # (x0, y0, x1, y1)
    center: Tuple[int, int]
    text: str
    confidence: float
    latency_ms: float


class Vision:
    """Screen perception layer: grab, map, and ground UI elements."""

    GRID_STEP = 10  # px between grid overlay lines

    def __init__(self, env: Any) -> None:
        self.env = env

    # ------------------------------------------------------------------
    def screen_grab(self) -> Dict[str, Any]:
        """Capture the current screen (framebuffer + metadata)."""
        t0 = time.perf_counter()
        fb = self.env.framebuffer()
        meta = {"width": self.env.width, "height": self.env.height,
                "n_windows": len(self.env.windows)}
        latency = (time.perf_counter() - t0) * 1000.0
        return {"framebuffer": fb, "meta": meta, "latency_ms": latency}

    # ------------------------------------------------------------------
    def grid_overlay(self, fb: str) -> str:
        """Draw a labelled coordinate grid over the framebuffer so the VLM
        can output well-calibrated (x, y) click targets."""
        lines = fb.rstrip("\n").split("\n")
        w = max(map(len, lines), default=0)
        header = "".join(str((c // self.GRID_STEP) % 10) for c in range(w))
        out = ["    " + header]
        for r, line in enumerate(lines):
            row_label = f"{r*self.GRID_STEP:03d}" if r % 2 == 0 else "   "
            out.append(row_label + " |" + line + "|")
        return "\n".join(out)

    # ------------------------------------------------------------------
    def ground_element(self, query: str) -> Optional[GroundedElement]:
        """Locate a UI element by a natural-language reference.

        In production this query is sent to a VLM along with the gridded
        screenshot. Here we implement a deterministic local grounding over
        the framebuffer (exact substring then fuzzy token match).
        """
        t0 = time.perf_counter()
        fb = self.env.framebuffer()
        lines = fb.rstrip("\n").split("\n")

        # 1) exact / substring match of the query text
        if not isinstance(query, str) or not query.strip():
            return None
        needle = query.strip().strip('\'"')
        for r, line in enumerate(lines):
            c = line.find(needle)
            if c >= 0:
                lat = (time.perf_counter() - t0) * 1000.0
                return GroundedElement(
                    query=query, bbox=(c, r * self.GRID_STEP,
                                       c + len(needle), (r + 1) * self.GRID_STEP),
                    center=(c + len(needle) // 2, r * self.GRID_STEP + self.GRID_STEP // 2),
                    text=needle, confidence=1.0, latency_ms=lat)

        # 2) token-level fuzzy match (>= 60% of query tokens present on a line)
        tokens = [t for t in re.split(r"\W+", needle.lower()) if len(t) > 2]
        best: Optional[Tuple[float, int, int, str]] = None
        for r, line in enumerate(lines):
            ll = line.lower()
            hits = sum(1 for t in tokens if t in ll)
            score = hits / max(1, len(tokens))
            if score >= 0.6 and (best is None or score > best[0]):
                c = min((ll.find(t) for t in tokens if ll.find(t) >= 0),
                        default=0)
                best = (score, r, c, line.strip())
        if best:
            score, r, c, _ = best
            lat = (time.perf_counter() - t0) * 1000.0
            return GroundedElement(
                query=query, bbox=(c, r * self.GRID_STEP, c + len(needle),
                                   (r + 1) * self.GRID_STEP),
                center=(c + max(1, len(needle) // 2),
                        r * self.GRID_STEP + self.GRID_STEP // 2),
                text=needle, confidence=round(score, 2), latency_ms=lat)

        return None

    # ------------------------------------------------------------------
    def ocr(self) -> List[str]:
        """Extract all readable text lines from the current screen."""
        fb = self.env.framebuffer()
        lines = [l.strip() for l in fb.rstrip("\n").split("\n") if l.strip()]
        return [re.sub(r"[|+\-]+", " ", l).strip() for l in lines if re.sub(r"[|+\-]+", " ", l).strip()]

    def observe(self) -> Dict[str, Any]:
        """Full observation bundle handed to the agent's ReAct loop."""
        grab = self.screen_grab()
        return {
            "screenshot": self.grid_overlay(grab["framebuffer"]),
            "raw_framebuffer": grab["framebuffer"],
            "ocr_text": [line.strip() for line in grab["framebuffer"].splitlines() if line.strip()],
            "meta": grab["meta"],
            "grab_latency_ms": grab["latency_ms"],
        }
