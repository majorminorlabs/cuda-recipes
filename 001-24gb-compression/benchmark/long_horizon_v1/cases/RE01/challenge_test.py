from requests.sessions import merge_setting

def test_long_horizon_re01():
    assert merge_setting({"verify": None}, {"verify": "/ca.pem", "timeout": 3}) == {"timeout": 3}
