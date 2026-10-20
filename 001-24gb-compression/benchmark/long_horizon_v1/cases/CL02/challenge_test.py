import click

def test_long_horizon_cl02(monkeypatch):
    values = iter(["  YES  "])
    monkeypatch.setattr(click.termui, "_readline_prompt", lambda *args, **kwargs: next(values))
    assert click.confirm("Continue?") is True
