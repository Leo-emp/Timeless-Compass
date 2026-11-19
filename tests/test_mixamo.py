from tc import mixamo


def test_export_body_asks_for_fbx_without_skin_at_30_fps_and_no_keyframe_reduction():
    gms = {"model-id": 7, "mirror": False, "trim": [0, 100], "overdrive": 0, "params": [["Posture", 0.5], ["Arm Space", 0.25]],
           "arm-space": 0, "inplace": False}
    body = mixamo.export_body("char-1", "Breathing Idle", gms)
    assert body["character_id"] == "char-1" and body["product_name"] == "Breathing Idle" and body["type"] == "Motion"
    assert body["preferences"] == {"format": "fbx7_2019", "skin": "false", "fps": "30", "reducekf": "0"}
    g = body["gms_hash"][0]
    assert g["params"] == "0.5,0.25" and g["inplace"] is False and g["model-id"] == 7


def test_best_match_prefers_exact_name_then_first_result():
    results = [{"name": "Walking Backwards", "id": "a"}, {"name": "Walking", "id": "b"}]
    assert mixamo.best_match("walking", results)["id"] == "b"
    assert mixamo.best_match("stride", results)["id"] == "a"
    assert mixamo.best_match("x", []) is None


def test_file_name_is_safe():
    assert mixamo.file_name("Sword And Shield Slash (2)") == "sword_and_shield_slash_2.fbx"
