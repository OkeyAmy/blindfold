# blindfold fixtures. Each assertion's expected status is encoded by the line content;
# the self-test checks blindfold classifies each correctly.

def price(p):
    return p * 0.8


def slug(s):
    return s.lower().replace(" ", "-")


def test_justified_inline():
    assert price(100) == 80.0  # blindfold: spec — 20% off $100 is $80


def test_justified_above():
    # blindfold: math — slug lowercases and turns spaces into dashes
    assert slug("A B") == "a-b"


def test_unjustified():
    assert price(50) == 40.0


def test_confessed():
    assert price(20) == 16.0  # blindfold: output — copied what the function returned


def test_trivial_exempt():
    assert price(0) == 0  # trivial literal, no reason required
