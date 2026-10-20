import attr

def test_long_horizon_at01():
    @attr.define
    class Child:
        value: int
    @attr.define
    class Parent:
        child: Child
    assert attr.asdict(Parent(Child(8))) == {"child": {"value": 8}}
