from src.template_automation import auth


def test_has_all_scopes_true_when_superset():
    granted = auth.SCOPES + ["https://www.googleapis.com/auth/extra"]
    assert auth._has_all_scopes(granted) is True


def test_has_all_scopes_false_when_missing_one():
    granted = [s for s in auth.SCOPES if "gmail" not in s]
    assert auth._has_all_scopes(granted) is False


def test_has_all_scopes_false_when_none():
    assert auth._has_all_scopes(None) is False
