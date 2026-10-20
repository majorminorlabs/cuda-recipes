import pytest
from more_itertools import chunked

def test_long_horizon_mi01():
    chunks = iter(chunked([1, 2, 3, 4, 5], 2, strict=True))
    assert next(chunks) == [1, 2]
    assert next(chunks) == [3, 4]
    with pytest.raises(ValueError, match="not divisible"):
        next(chunks)
