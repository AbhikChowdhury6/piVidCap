import glob
import shutil
import threading
import time
from datetime import datetime, timezone

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


def test_exit_video_survives_vanished_temp_file(tmp_path, monkeypatch):
    """Regression test for the 2026-07-28 upload-race crash: if the day's
    folder (and thus the in-progress temp file) vanishes out from under a
    live writer_worker -- e.g. an upload script deleting it -- exitVideo()
    must not crash with an unhandled FileNotFoundError."""
    monkeypatch.setattr(writerWorker, "baseFilePath", str(tmp_path) + "/collectedData/testdevice_")

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
    time.sleep(17)  # let a real VideoWriter open + write past the first 15s tick

    # simulate the race: an upload script deletes the whole day folder
    # (temp file included) while writer_worker still holds it open
    for d in glob.glob(str(tmp_path) + "/collectedData/testdevice_*"):
        shutil.rmtree(d)

    exit_signal[0] = 1  # triggers exitVideo() on the now-vanished tempFilePath
    t.join(timeout=10)

    assert not t.is_alive(), "writer_worker did not exit after exit signal within 10s"
    assert "error" not in failure, f"writer_worker crashed: {failure.get('error')}"
