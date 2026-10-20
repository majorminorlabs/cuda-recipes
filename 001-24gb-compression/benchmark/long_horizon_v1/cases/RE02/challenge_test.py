from requests.sessions import merge_hooks

def test_long_horizon_re02():
    seen = []
    callback = lambda response, **kwargs: seen.append(response)
    assert merge_hooks({"response": []}, {"response": [callback]}) == {"response": [callback]}
