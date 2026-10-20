from packaging.utils import canonicalize_version

def test_long_horizon_pk02():
    assert canonicalize_version("1.4.0.0", strip_trailing_zero=False) == "1.4.0.0"
    assert canonicalize_version("1.4.0.0", strip_trailing_zero=True) == "1.4"
