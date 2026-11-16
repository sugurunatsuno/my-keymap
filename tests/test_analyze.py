import csv
import gzip
import json
from pathlib import Path

import pytest

from keylab.analyze import analyze_rows, analyze_session


def row(t, frame, x, hand="Left", lid=8):
    return {"session_time_s": t, "frame_index": frame, "x_norm": x,
            "y_norm": 0.5, "hand": hand, "landmark_id": lid}


def test_distance_speed_and_coverage():
    results = analyze_rows([row(0, 0, 0), row(0.1, 1, 0.1), row(0.2, 2, 0.2)],
                           width=100, height=100, processed_frames=4)
    assert len(results) == 1
    result = results[0]
    assert result["finger"] == "index"
    assert result["total_path_px"] == 20
    assert result["mean_speed_px_s"] == 100
    assert result["segments"] == 2
    assert result["coverage"] == 0.75


def test_tracking_gap_does_not_become_a_jump():
    result = analyze_rows([row(0, 0, 0), row(2, 1, 0.8)],
                          width=100, height=100, processed_frames=2)[0]
    assert result["total_path_px"] == 0
    assert result["segments"] == 0


def test_end_to_end_report(tmp_path: Path):
    (tmp_path / "metadata.json").write_text(json.dumps({
        "frame_width": 200, "frame_height": 100, "processed_frames": 2
    }), encoding="utf-8")
    with gzip.open(tmp_path / "landmarks.csv.gz", "wt", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row(0, 0, 0).keys())
        writer.writeheader()
        writer.writerow(row(0, 0, 0.1))
        writer.writerow(row(0.1, 1, 0.2))
    report = analyze_session(tmp_path)
    assert report["summary"][0]["total_path_px"] == 20
    assert (tmp_path / "summary.csv").exists()
    assert (tmp_path / "summary.json").exists()


def test_invalid_metadata():
    with pytest.raises(ValueError):
        analyze_rows([], 0, 100, 3)

def test_wrist_and_finger_translation():
    data = [
        row(0, 0, 0.1, lid=0), row(0, 0, 0.2, lid=8),
        row(0.1, 1, 0.2, lid=0), row(0.1, 1, 0.3, lid=8),
    ]
    by_finger = {x["finger"]: x for x in analyze_rows(data, 100, 100, 2)}
    assert by_finger["wrist"]["total_path_px"] == 10
    assert by_finger["index"]["total_path_px"] == 10
    assert by_finger["index"]["wrist_relative_path_px"] == 0
    assert by_finger["index"]["wrist_relative_segments"] == 1


def test_stationary_wrist_moving_finger():
    data = [
        row(0, 0, 0.1, lid=0), row(0, 0, 0.2, lid=8),
        row(0.1, 1, 0.1, lid=0), row(0.1, 1, 0.3, lid=8),
    ]
    by_finger = {x["finger"]: x for x in analyze_rows(data, 100, 100, 2)}
    assert by_finger["wrist"]["total_path_px"] == 0
    assert by_finger["index"]["wrist_relative_path_px"] == 10


def test_no_wrist_is_missing_not_zero():
    r = analyze_rows([row(0, 0, 0.1), row(0.1, 1, 0.2)], 100, 100, 2)[0]
    assert r["wrist_relative_path_px"] is None
    assert r["wrist_relative_segments"] == 0

