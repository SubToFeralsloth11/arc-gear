# Arc Gear

Procedural Blender models of Arc Raiders-inspired gear. Every model is a Python script, and the textures are procedural materials: worn paint, primer, bare-metal chips, grime and sand.

| Script | Item |
|---|---|
| `models/rifle.py` | HCR-1 "Breaker", a heavy single-shot rifle |
| `models/smg.py` | Compact SMG with wire stock and reflex sight |
| `models/ar.py` | Assault rifle with curved mag and holo sight |
| `models/pickaxe.py` | Raider pickaxe |
| `models/impact_grenade.py` | Impact grenade with glowing contact pins |
| `models/smoke_grenade.py` | Vented smoke grenade with spoon and pin |
| `models/shield_recharger.py` | Handheld shield recharger cell |
| `models/bandage.py` | Elastic bandage roll plus field-dressing pouch |
| `models/raider.py` | Original scavenger raider character: respirator, goggles, helmet, layered jacket and trousers, chest rig, belt pouches, backpack with bedroll (needs the MPFB extension) |

`kit.py` holds the shared materials, geometry helpers, studio lighting and render setup.

```sh
blender -b -P models/smg.py             # full quality: out/smg.blend + out/smg_*.png
blender -b -P models/smg.py -- quick    # half-res, low samples
blender -b -P models/smg.py -- hero     # only the named camera
```

The raider is grown from an anatomical MakeHuman (MPFB) body. Each garment is a shell taken from the body surface, then inflated, relaxed, trimmed, subdivided, given cloth folds and thickened. The full build also exports `out/raider.glb` with every modifier applied, at several million triangles. It is a static model in the A-pose, with no rig.

The procedural materials render in Blender (Cycles). Exporting to a game engine needs the textures baked to images first.
