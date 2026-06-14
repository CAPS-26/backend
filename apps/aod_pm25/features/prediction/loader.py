"""Model loader abstraction supporting TensorFlow (Keras) and PyTorch.

Usage:
    model = await load_model_from_file(path)

This function offloads blocking I/O / CPU work to a thread.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


async def load_model_from_file(path: str) -> Any:
    """Detect model type from file extension and load appropriately.

    Supported:
    - TensorFlow Keras (.keras, .h5)
    - PyTorch (.pt, .pth)
    """
    ext = Path(path).suffix.lower()

    if ext in {".keras", ".h5"}:
        # Lazy import tensorflow to avoid heavy startup when not needed
        from tensorflow.keras.models import load_model as _tf_load  # noqa: PLC0415

        return await asyncio.to_thread(_tf_load, path)

    if ext in {".pt", ".pth"}:
        # Lazy import torch
        import torch  # noqa: PLC0415

        def _load_torch(p: str):
            try:
                # Try torch.jit first
                return torch.jit.load(p)
            except Exception:
                return torch.load(p, map_location="cpu")

        return await asyncio.to_thread(_load_torch, path)

    raise ValueError(f"Unsupported model file extension: {ext}")
