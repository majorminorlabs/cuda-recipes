from more_itertools import split_before

def test_long_horizon_mi02():
    assert list(split_before("a,b,c,d", lambda ch: ch == ",", maxsplit=2)) == [
        ["a"], [",", "b"], [",", "c", ",", "d"]
    ]
