import pytest

from apps.aod_pm25.features.prediction.loader import load_model_from_file


@pytest.mark.asyncio
async def test_loader_unsupported_extension(tmp_path):
    with pytest.raises(ValueError):
        test_path = tmp_path / "model.unknown_ext"
        await load_model_from_file(str(test_path))
