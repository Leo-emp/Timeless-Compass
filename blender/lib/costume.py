# COSTUMES: one call dresses a body in a complete, era-correct outfit by WARDROBE NAME (library/wardrobe/*.json), using
# the garment builders in wardrobe.py (Session D, WS3) exactly as blender/scenes/ws3_wardrobe.py + xerxes_v2.py assemble
# them. Cloth is simulated and frozen by the builders; with bind=True every frozen garment is then skinned to the
# skeleton, so it moves with mocap / poses (extras and most shots). Hero shots with big motion can still use
# wardrobe.chiton/himation + settle_then_follow for live cloth.
#   dress(human, rig, pos, 'greek_woman_480bc', dye=person['dye'], seed=7)  -> [garment objects]
import bpy

from lib import common, wardrobe

SAFFRON, MADDER, WOAD = (0.45, 0.30, 0.10), (0.30, 0.05, 0.035), (0.07, 0.10, 0.26)
UNDYED, WHITE_LINEN, PURPLE, CRIMSON = (0.50, 0.46, 0.38), (0.60, 0.57, 0.50), (0.20, 0.02, 0.12), (0.42, 0.04, 0.06)
GOLD_THREAD = (0.6, 0.45, 0.15)


def _cloth(name, dye, seed, wool=False):
    """Rank-aware cloth (WS3 crowd_cloth: dyes, grime, patches) from a crowd dye dict, or a plain era dye."""
    if isinstance(dye, dict):
        return wardrobe.crowd_cloth(name, dye, wool=wool, seed=seed)
    scan = 'caban' if wool else 'rough_linen'
    return wardrobe.scan_cloth(name, scan, dye, tiles=(4, 12) if wool else (7, 5), grime=0.2, sheen=0.15)


def _metals():
    gold = bpy.data.materials.get('costume_gold') or common.principled('costume_gold', (0.83, 0.62, 0.26), metal=1.0, rough=0.3)
    leather = bpy.data.materials.get('costume_leather') or common.principled('costume_leather', (0.22, 0.13, 0.07), rough=0.75, bump=0.3, bump_scale=200)
    return gold, leather


def dress(human, rig, pos, wardrobe_name, dye=None, seed=0, bind=True, rich=None):
    """Dress `human` in `wardrobe_name`; returns the new garment objects. `rich` adds the extra layers of wealth
    (mantle, veil, jewellery) - default: from dye['rank']."""
    before = set(bpy.data.objects)
    rank = (dye or {}).get('rank', 'common') if isinstance(dye, dict) else 'common'
    rich = rich if rich is not None else rank in ('rich', 'royal')
    gold, leather = _metals()
    w = wardrobe_name or 'greek_civilian_480bc'
    main = dye if dye is not None else UNDYED
    blend = w in ('greek_woman_480bc', 'greek_servant_480bc', 'greek_child_480bc', 'persian_woman_480bc')
    if blend:                       # Session D: peplos / exomis / child_tunic are BLEND garments - the cloth settles
        from lib import pose       # while the hands move away from the hips (else the hands push the skirt open)
        wardrobe._ensure_poses()
        pose.blend_into_pose(rig, 'stand_open', 1, 15)
    def _fix_pose():                # after the blend garment: freeze the final pose, then rigid extras (veil, belt...)
        if blend:
            rig.animation_data_clear()
            pose.apply_pose(rig, 'stand_open')
    if w == 'greek_woman_480bc':
        body, over = wardrobe.peplos(human, rig, pos, _cloth(f'peplos_{seed}', main, seed, wool=True), belt_over=True)
        _fix_pose()
        wardrobe.belt(rig, over, _cloth(f'girdle_{seed}', MADDER, seed, wool=True))
        wardrobe.sandals(human, rig, leather)
        if rich:
            wardrobe.veil(human, rig, _cloth(f'veil_{seed}', UNDYED, seed, wool=True))
            wardrobe.earrings(human, rig, gold)
        if rank == 'royal' or rich == 'royal':
            wardrobe.diadem(human, rig, gold)
    elif w == 'greek_servant_480bc':
        ex = wardrobe.exomis(human, rig, pos, _cloth(f'exomis_{seed}', main, seed))
        _fix_pose()
        wardrobe.belt(rig, ex, common.principled(f'rope_{seed}', (0.24, 0.18, 0.11), rough=0.9, bump=0.4, bump_scale=300))
    elif w == 'greek_child_480bc':
        t = wardrobe.child_tunic(human, rig, pos, _cloth(f'child_{seed}', main, seed))
        _fix_pose()
        wardrobe.belt(rig, t, _cloth(f'child_girdle_{seed}', WOAD, seed, wool=True), max_r=0.13)
    elif w in ('greek_priest_480bc', 'greek_priestess_480bc'):
        female = w.endswith('priestess_480bc')
        wardrobe.priest_robes(human, rig, pos, _cloth(f'ritual_linen_{seed}', WHITE_LINEN, seed),
                              _cloth(f'ritual_wool_{seed}', UNDYED, seed, wool=True), female=female)
        wardrobe.sandals(human, rig, leather)
        if female:
            wardrobe.diadem(human, rig, gold)
    elif w == 'persian_king_480bc':                               # Xenophon: purple robe, crimson trousers, upright tiara
        wardrobe.trousers(human, rig, _cloth(f'royal_trousers_{seed}', CRIMSON, seed, wool=True))
        # the under-tunic (Xenophon, Cyropaedia 8.3.13: a purple tunic with a white middle under the robe) closes the
        # chest - without it the open front of the robe shows bare skin
        wardrobe.median_tunic(human, rig, pos, wardrobe.scan_cloth(f'royal_tunic_{seed}', 'rough_linen', PURPLE, tiles=(7, 5), sheen=0.15))
        wardrobe.candys(human, rig, pos, wardrobe.scan_cloth(f'royal_robe_{seed}', 'rough_linen', PURPLE, band=GOLD_THREAD, tiles=(7, 5), sheen=0.2))
        wardrobe.wide_sleeves(human, rig, wardrobe.scan_cloth(f'royal_sleeves_{seed}', 'rough_linen', PURPLE, band=GOLD_THREAD, tiles=(7, 5)))
        wardrobe.persian_cap(human, rig, _cloth(f'royal_felt_{seed}', PURPLE, seed, wool=True), band=gold, kind='royal')
    elif w == 'persian_woman_480bc':                              # Persepolis seals: long robe to the feet + veil, no cap
        body, over = wardrobe.peplos(human, rig, pos, _cloth(f'robe_{seed}', main, seed, wool=True), belt_over=True)
        _fix_pose()
        wardrobe.belt(rig, over, _cloth(f'sash_{seed}', GOLD_THREAD if rich else MADDER, seed, wool=True))
        wardrobe.veil(human, rig, _cloth(f'pveil_{seed}', WHITE_LINEN if rich else UNDYED, seed))
        wardrobe.sandals(human, rig, leather)
        if rich:
            wardrobe.earrings(human, rig, gold)
            wardrobe.necklace(human, rig, gold) if hasattr(wardrobe, 'necklace') else None
    elif w.startswith('persian_'):                                # courtiers, soldiers, servants (men): Median dress
        wardrobe.trousers(human, rig, _cloth(f'mede_trousers_{seed}', main if rich else (0.3, 0.06, 0.04), seed, wool=True))
        wardrobe.median_tunic(human, rig, pos, _cloth(f'mede_tunic_{seed}', main, seed))
        wardrobe.tight_sleeves(human, rig, _cloth(f'mede_sleeves_{seed}', main, seed))
        wardrobe.persian_cap(human, rig, _cloth(f'mede_felt_{seed}', (0.4, 0.33, 0.24), seed, wool=True), kind='median')
    else:                                                         # Greek men: chiton (+ himation for the better-off)
        ch = wardrobe.chiton(human, rig, pos, _cloth(f'chiton_{seed}', main, seed))
        wardrobe.simulate(40); wardrobe.freeze(ch)
        if rich:
            hm = wardrobe.himation(human, rig, pos, _cloth(f'himation_{seed}', MADDER if rank != 'royal' else PURPLE, seed, wool=True),
                                   side='L', over=ch)
            wardrobe.simulate(55); wardrobe.freeze(hm)
        wardrobe.sandals(human, rig, leather)
    new = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    if bind:                                                      # frozen garments follow the skeleton (skinned)
        for g in new:
            if g.parent is None:
                try:
                    wardrobe.bind_to_skeleton(g, human, rig)
                except Exception as e:
                    print('bind skipped', g.name, e)
    return new
