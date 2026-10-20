import click

def test_long_horizon_cl01(monkeypatch):
    monkeypatch.setattr(click.termui, "_readline_prompt", lambda *args, **kwargs: "")
    assert click.prompt("Count", default="7", type=int) == 7
    assert type(click.prompt("Count", default="7", type=int)) is int
