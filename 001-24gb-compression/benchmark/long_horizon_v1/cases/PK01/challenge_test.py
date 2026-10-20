from packaging.utils import canonicalize_name

def test_long_horizon_pk01():
    assert canonicalize_name("Acme._--Tools") == "acme-tools"
    assert canonicalize_name("acme....tools") == "acme-tools"
