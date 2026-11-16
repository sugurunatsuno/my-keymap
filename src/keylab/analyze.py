"""Pure-Python analysis of fingertip movement in a fixed camera frame."""

import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

FINGERTIPS = {4: "thumb", 8: "index", 12: "middle", 16: "ring", 20: "pinky"}
MAX_GAP_S = 0.2


def analyze_rows(rows, width, height, processed_frames, max_gap_s=MAX_GAP_S):
    """Return per-finger aggregates; no inference of keypresses or ergonomics."""
    if width <= 0 or height <= 0 or processed_frames <= 0:
        raise ValueError("width, height, processed_frames must be positive")
    tracks = defaultdict(list)
    for row in rows:
        lid = int(row["landmark_id"])
        if lid not in FINGERTIPS:
            continue
        label = row["hand"]
        if label not in {"Left", "Right"}:
            continue
        tracks[(label, lid)].append((
            float(row["session_time_s"]),
            float(row["x_norm"]) * width,
            float(row["y_norm"]) * height,
            int(row["frame_index"]),
        ))

    summaries = []
    for (hand, lid), points in sorted(tracks.items()):
        points.sort(key=lambda p: (p[0], p[3]))
        total_px = 0.0
        speeds = []
        valid_segments = 0
        for prev, curr in zip(points, points[1:]):
            dt = curr[0] - prev[0]
            if 0 < dt <= max_gap_s and curr[3] > prev[3]:
                distance = math.hypot(curr[1] - prev[1], curr[2] - prev[2])
                total_px += distance
                speeds.append(distance / dt)
                valid_segments += 1
        observed = len({p[3] for p in points})
        summaries.append({
            "hand": hand,
            "finger": FINGERTIPS[lid],
            "landmark_id": lid,
            "observed_frames": observed,
            "coverage": round(min(1.0, observed / processed_frames), 4),
            "segments": valid_segments,
            "total_path_px": round(total_px, 2),
            "mean_speed_px_s": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
        })
    return summaries


def analyze_session(session_dir: Path):
    session_dir = Path(session_dir)
    metadata_path = session_dir / "metadata.json"
    landmarks_path = session_dir / "landmarks.csv.gz"
    if not metadata_path.exists() or not landmarks_path.exists():
        raise FileNotFoundError("session must contain metadata.json and landmarks.csv.gz")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with gzip.open(landmarks_path, "rt", encoding="utf-8", newline="") as infile:
        rows = csv.DictReader(infile)
        results = analyze_rows(
            rows, metadata["frame_width"], metadata["frame_height"],
            metadata["processed_frames"],
        )
    report = {
        "session": session_dir.name,
        "metrics_unit": "pixels in uncalibrated camera frame",
        "summary": results,
        "warnings": [
            "Video alone cannot infer the pressed keys or typing performance.",
            "Only compare sessions with identical camera placement and resolution.",
        ],
    }
    (session_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (session_dir / "summary.csv").open("w", encoding="utf-8", newline="") as outfile:
        fields = ["hand", "finger", "landmark_id", "observed_frames", "coverage",
                  "segments", "total_path_px", "mean_speed_px_s"]
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    return report
