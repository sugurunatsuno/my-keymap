"""Command line entry point for local-only research utilities."""

import argparse
import sys
import urllib.request
from pathlib import Path
from .analyze import analyze_session

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def build_parser():
    parser = argparse.ArgumentParser(prog="keylab", description="Local-first keyboard layout research")
    sub = parser.add_subparsers(dest="command", required=True)

    model = sub.add_parser("download-model", help="Explicitly download the MediaPipe model")
    model.add_argument("--output", type=Path, default=Path("models/hand_landmarker.task"))

    cam = sub.add_parser("capture", help="Capture hand landmarks from a local camera")
    cam.add_argument("--camera", type=int, default=0)
    cam.add_argument("--model", type=Path, default=Path("models/hand_landmarker.task"))
    cam.add_argument("--output-root", type=Path, default=Path("data/sessions"))
    cam.add_argument("--duration", type=float, default=60)
    cam.add_argument("--preview", action="store_true")
    cam.add_argument("--save-video", action="store_true", help="Opt in to saving raw MP4 video")
    cam.add_argument("--width", type=int, default=1280)
    cam.add_argument("--height", type=int, default=720)
    cam.add_argument("--layout", default="unspecified", help="Layout used during the session")
    cam.add_argument("--input-method", default="romaji", help="Input method, e.g. romaji")
    cam.add_argument("--task-id", default="unstructured", help="Identifier of the typing task")

    report = sub.add_parser("analyze", help="Summarize movements from a recorded session")
    report.add_argument("session_dir", type=Path, nargs="?")
    report.add_argument("--latest", action="store_true", help="Analyze newest data/sessions directory")
    heatmap = sub.add_parser("heatmap", help="Create a local Japanese romaji key-frequency heatmap")
    heatmap.add_argument("input_file", type=Path, help="UTF-8 input text")
    heatmap.add_argument("--layout", type=Path, default=Path("layouts/personal-colemak-derived-65.json"))
    heatmap.add_argument("--out-dir", type=Path, default=Path("reports/heatmap"))
    heatmap.add_argument("--mode", choices=("auto", "kana", "romaji"), default="auto")
    heatmap.add_argument("--n-style", choices=("double", "contextual"), default="double")
    heatmap.add_argument("--small-kana-style", choices=("l", "x"), default="l",
                         help="Prefix for isolated small kana (default: l)")
    comparison = sub.add_parser("heatmap-compare", help="Compare normal, trial8 and all35 suffix IME heatmaps")
    comparison.add_argument("input_file", type=Path, help="UTF-8 Japanese input text")
    comparison.add_argument("--layout", type=Path,
                            default=Path("layouts/personal-colemak-derived-65-ue-swap-v2.json"))
    comparison.add_argument("--lexicon", type=Path, default=Path("lexicons/effiveroman-suffixes.tsv"))
    comparison.add_argument("--out-dir", type=Path, default=Path("reports/ime-compare"))
    comparison.add_argument("--n-style", choices=("double", "contextual"), default="double")
    comparison.add_argument("--small-kana-style", choices=("l", "x"), default="l")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "download-model":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.exists():
                print(f"Model exists: {args.output} (not overwritten)")
                return
            temp = args.output.with_suffix(".task.partial")
            try:
                urllib.request.urlretrieve(MODEL_URL, temp)
                if temp.stat().st_size < 100_000:
                    raise RuntimeError("Downloaded model is unexpectedly small")
                temp.replace(args.output)
            finally:
                temp.unlink(missing_ok=True)
            print(f"Model downloaded: {args.output}")
        elif args.command == "capture":
            from .capture import capture
            path = capture(args.camera, args.model, args.output_root, args.duration,
                           args.preview, args.save_video, args.width, args.height,
                           args.layout, args.input_method, args.task_id)
            print(f"Session saved locally: {path}")
            print(f"Analyze with: python -m keylab analyze {path}")
        elif args.command == "analyze":
            if args.latest:
                if args.session_dir is not None:
                    raise ValueError("Specify a session path OR --latest, not both")
                directories = sorted(p for p in Path("data/sessions").glob("*") if p.is_dir())
                if not directories:
                    raise FileNotFoundError("No sessions in data/sessions")
                session_dir = directories[-1]
            else:
                if args.session_dir is None:
                    raise ValueError("Specify a session path or --latest")
                session_dir = args.session_dir
            report = analyze_session(session_dir)
            print(f"Analyzed {len(report['summary'])} fingertip tracks")
            print(f"Wrote {session_dir / 'summary.csv'}")
        elif args.command == "heatmap":
            from .heatmap import generate_heatmap
            summary = generate_heatmap(args.input_file, args.layout, args.out_dir,
                                       args.mode, args.n_style, args.small_kana_style)
            print(f"Estimated keypresses: {summary['estimated_keypresses']:,}")
            print(f"HTML: {args.out_dir / 'heatmap.html'}")
            print(f"CSV: {args.out_dir / 'key_counts.csv'}")
            print(f"JSON: {args.out_dir / 'summary.json'}")
        elif args.command == "heatmap-compare":
            from .ime_heatmap import compare_ime_heatmaps
            report = compare_ime_heatmaps(
                args.input_file, args.layout, args.lexicon, args.out_dir,
                args.n_style, args.small_kana_style)
            for mode in ("none", "trial", "all"):
                row = report["scenarios"][mode]
                print(f"{mode}: {row['estimated_keypresses']} keys"
                      f" (saved: {row['saved_vs_none']})")
            print(f"Open: {args.out_dir / 'index.html'}")
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
