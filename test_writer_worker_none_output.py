import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import torch

import writerWorker


def _make_ctsb(num_frames=5, height=4, width=4):
    class FakeCtsb:
        pass

    ctsb = FakeCtsb()
    ctsb.bn = torch.zeros(1, dtype=torch.int32)
    ctsb.lengths = torch.zeros((3, 1), dtype=torch.int32)
    for b in range(3):
        ctsb.lengths[b][0] = num_frames
    ctsb.data_buffers = torch.zeros((3, num_frames, height, width, 3), dtype=torch.uint8)
    now_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
    ctsb.time_buffers = torch.zeros((3, num_frames), dtype=torch.int64)
    for b in range(3):
        for i in range(num_frames):
            ctsb.time_buffers[b][i] = now_ns + i * 100_000_000
    return ctsb


def test_writer_worker_survives_failed_video_writer_open(tmp_path, monkeypatch):
    """Regression test for the 2026-07-28 outage: a VideoWriter that fails to
    open must not crash writer_worker with an unhandled AttributeError."""
    monkeypatch.setattr(writerWorker, "baseFilePath", str(tmp_path) + "/collectedData/testdevice_")

    fake_writer = MagicMock()
    fake_writer.isOpened.return_value = False
    monkeypatch.setattr(writerWorker.cv2, "VideoWriter", MagicMock(return_value=fake_writer))

    ctsb = _make_ctsb()
    person_signal = torch.zeros(1, dtype=torch.int8)
    person_signal[0] = 1  # force the rising-edge branch to fire on the first tick
    exit_signal = torch.zeros(1, dtype=torch.int64)

    failure = {}

    def run():
        try:
            writerWorker.writer_worker(ctsb, person_signal, exit_signal)
        except Exception as e:  # noqa: BLE001 - we want to catch and inspect anything
            failure["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(17)  # writer_worker aligns to the next real 15s wall-clock boundary
    exit_signal[0] = 1
    t.join(timeout=10)

    assert not t.is_alive(), "writer_worker did not exit after exit signal within 10s"
    assert "error" not in failure, f"writer_worker crashed: {failure.get('error')}"
