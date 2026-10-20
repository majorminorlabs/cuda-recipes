import pytest
from attr.converters import to_bool

@pytest.mark.parametrize(("value", "expected"), [(" true ", True), (" OFF ", False), (" 1 ", True), (" 0 ", False)])
def test_long_horizon_at02(value, expected):
    assert to_bool(value) is expected
