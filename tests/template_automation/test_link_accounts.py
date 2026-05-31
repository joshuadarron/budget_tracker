import link_accounts


def test_build_link_request_includes_redirect_uri_when_given():
    req = link_accounts.build_link_request("chase", "https://localhost:5000/oauth")
    assert req["redirect_uri"] == "https://localhost:5000/oauth"


def test_build_link_request_omits_redirect_uri_when_none():
    req = link_accounts.build_link_request("chase", None)
    assert "redirect_uri" not in req.to_dict()


def test_build_link_request_sets_user_and_products():
    req = link_accounts.build_link_request("schoolsfirst", None)
    assert req["user"]["client_user_id"] == "schoolsfirst"
    assert [str(p.value) for p in req["products"]] == ["transactions"]
