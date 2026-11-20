# MAP SPEC CHECKS: catch mistakes in a map spec before minutes of painting (and before a render is wasted).
ICONS = {"city", "capital", "fort", "crown", "none"}
BEATS = {"grow", "shrink", "show", "hide", "arrow", "pulse", "battle", "spotlight", "unspot", "date", "move", "card", "uncard"}


def _ll(p) -> bool:
    return isinstance(p, (list, tuple)) and len(p) == 2 and -180 <= p[0] <= 180 and -90 <= p[1] <= 90


def problems(spec: dict) -> list[str]:
    """Every problem found (empty list = good)."""
    out = []
    v = spec.get("view") or {}
    if not ("box" in v or ("center" in v and "span_lon" in v)):
        out.append("view needs either box [lon0,lat0,lon1,lat1] or center [lon,lat] + span_lon")
    ids = set()
    for kind in ("territories", "arrows", "pulses", "battles", "armies", "cards"):
        for i, t in enumerate(spec.get(kind, [])):
            if "id" not in t:
                out.append(f"{kind}[{i}] has no id"); continue
            if t["id"] in ids:
                out.append(f"duplicate id {t['id']}")
            ids.add(t["id"])
    for t in spec.get("territories", []):
        b = t.get("border", [])
        if len(b) < 3 or not all(_ll(p) for p in b):
            out.append(f"territory {t.get('id')}: border needs 3+ [lon, lat] points")
        for k in ("heart", "label_at"):
            if k in t and not _ll(t[k]):
                out.append(f"territory {t.get('id')}: {k} must be [lon, lat]")
    for a in spec.get("arrows", []):
        if len(a.get("path", [])) < 2 or not all(_ll(p) for p in a["path"]):
            out.append(f"arrow {a.get('id')}: path needs 2+ [lon, lat] points")
    for p in spec.get("places", []):
        if not _ll(p.get("at")) or not p.get("text"):
            out.append(f"place {p.get('text')}: needs text + at [lon, lat]")
        if p.get("icon", "city") not in ICONS:
            out.append(f"place {p.get('text')}: icon must be one of {sorted(ICONS)}")
    for i, b in enumerate(spec.get("beats", [])):
        if b.get("do") not in BEATS:
            out.append(f"beat {i}: do must be one of {sorted(BEATS)}")
        if b.get("do") not in ("date", "unspot") and b.get("id") not in ids and b.get("do") not in ("show", "hide", "spotlight"):
            out.append(f"beat {i}: unknown id {b.get('id')}")
        if not isinstance(b.get("t"), (int, float)):
            out.append(f"beat {i}: t (seconds) missing")
    return out
