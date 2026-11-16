"""Local camera capture; raw video saved only on explicit opt-in."""

import csv
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ["frame_index", "session_time_s", "hand", "hand_score", "hand_index",
           "landmark_id", "x_norm", "y_norm", "z_norm"]


def capture(camera, model, output_root, duration, preview, save_video, width, height,
            layout, input_method, task_id):
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Camera dependencies missing: pip install -e '.[camera]'") from exc

    model = Path(model)
    if not model.is_file():
        raise FileNotFoundError(f"MediaPipe model missing: {model}. Run 'python -m keylab download-model'")
    if duration <= 0:
        raise ValueError("--duration must be positive")

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Cannot open camera {camera}; check device, permissions and --camera")
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Do not mirror the image: MediaPipe handedness assumes a non-mirrored input.
    successful, first_frame = cap.read()
    if not successful:
        cap.release()
        raise RuntimeError("Camera opened but no frame could be read")
    frame_height, frame_width = first_frame.shape[:2]
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not (1 <= fps <= 120):
        fps = 30.0

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    session_dir = output_root / stamp
    session_dir.mkdir(exist_ok=False)
    video_writer = None
    processed = 0
    start = time.monotonic()  # fallback timestamp for setup errors
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        if save_video:
            path = session_dir / "session.mp4"
            video_writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_width, frame_height)
            )
            if not video_writer.isOpened():
                raise RuntimeError("Cannot initialize MP4 writer; check installed video codecs")

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
        )
        with gzip.open(session_dir / "landmarks.csv.gz", "wt", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=COLUMNS)
            writer.writeheader()
            with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector:
                fresh, frame = cap.read()
                if not fresh:
                    frame = first_frame
                start = time.monotonic()
                started_at = datetime.now(timezone.utc).isoformat()
                last_ms = -1
                while True:
                    now = time.monotonic()
                    elapsed = now - start
                    if elapsed >= duration:
                        break
                    if video_writer is not None:
                        video_writer.write(frame)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                        data=np.ascontiguousarray(rgb))
                    ts_ms = max(last_ms + 1, int(elapsed * 1000))
                    last_ms = ts_ms
                    result = detector.detect_for_video(mp_image, ts_ms)
                    for hand_idx, landmarks in enumerate(result.hand_landmarks):
                        categories = result.handedness[hand_idx]
                        category = categories[0] if categories else None
                        hand = category.category_name if category else "Unknown"
                        score = round(float(category.score), 4) if category else 0.0
                        for point_id, point in enumerate(landmarks):
                            writer.writerow({
                                "frame_index": processed,
                                "session_time_s": round(elapsed, 6),
                                "hand": hand,
                                "hand_score": score,
                                "hand_index": hand_idx,
                                "landmark_id": point_id,
                                "x_norm": round(float(point.x), 6),
                                "y_norm": round(float(point.y), 6),
                                "z_norm": round(float(point.z), 6),
                            })
                    processed += 1
                    if preview:
                        for hand in result.hand_landmarks:
                            for point_id in (4, 8, 12, 16, 20):
                                tip = hand[point_id]
                                cv2.circle(frame, (int(tip.x * frame_width),
                                                   int(tip.y * frame_height)), 4, (0, 255, 0), -1)
                        cv2.imshow("Keyboard Layout Lab (q to quit)", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                    ok, frame = cap.read()
                    if not ok:
                        break
    except KeyboardInterrupt:
        pass
    finally:
        if video_writer is not None:
            video_writer.release()
        cap.release()
        if preview:
            cv2.destroyAllWindows()
        metadata = {
            "started_at_utc": started_at,
            "camera_index": camera,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "camera_reported_fps": fps,
            "processed_frames": processed,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "video_saved": save_video,
            "video_audio": False,
            "model_path": model.name,
            "raw_key_events_logged": False,
            "layout": layout,
            "input_method": input_method,
            "task_id": task_id,
            "coordinate_system": "non-mirrored normalized camera image",
        }
        (session_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return session_dir
