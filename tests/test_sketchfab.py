from tc import sketchfab


def _m(uid, lic, name="Amphora", user="museum", faces=20000):
    return {"uid": uid, "name": name, "license": {"slug": lic}, "user": {"displayName": user},
            "faceCount": faces, "viewerUrl": f"https://sketchfab.com/3d-models/x-{uid}", "isDownloadable": True}


def test_only_youtube_safe_licences_are_allowed():
    assert sketchfab.allowed(_m("a", "cc0")) and sketchfab.allowed(_m("b", "by"))
    for bad in ("by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "by-sa", "st", "ed"):
        assert not sketchfab.allowed(_m("c", bad)), bad


def test_pick_prefers_cc0_then_lighter_models():
    results = [_m("heavy", "by", faces=900000), _m("light", "by", faces=30000), _m("free", "cc0", faces=200000),
               _m("nc", "by-nc", faces=1000)]
    assert [m["uid"] for m in sketchfab.pick(results, n=3)] == ["free", "light", "heavy"]


def test_credit_line_names_model_author_and_licence():
    line = sketchfab.credit(_m("u1", "by", name="Greek Amphora", user="British Museum"))
    assert "Greek Amphora" in line and "British Museum" in line and "CC BY" in line and "sketchfab.com" in line
    assert sketchfab.credit(_m("u2", "cc0")).endswith("(CC0)")


def test_licence_labels_from_search_results_are_understood():
    m = {"uid": "x", "name": "A", "license": {"label": "CC Attribution"}, "user": {"displayName": "u"}, "faceCount": 1}
    assert sketchfab.allowed(m)
    m["license"] = {"label": "CC0 Public Domain"}; assert sketchfab.allowed(m)
    m["license"] = {"label": "CC Attribution-NonCommercial-ShareAlike"}; assert not sketchfab.allowed(m)
