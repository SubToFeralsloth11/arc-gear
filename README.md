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
| `models/raider_anim.py` | Procedural animation set for the raider: heavy, gear-laden locomotion, rifle holds, reload, throw, loot, roll |
| `models/game_export.py` | Bakes the procedural materials to textures and writes game GLBs for the raider and all gear |

`kit.py` holds the shared materials, geometry helpers, studio lighting and render setup.

```sh
blender -b -P models/smg.py             # full quality: out/smg.blend + out/smg_*.png
blender -b -P models/smg.py -- quick    # half-res, low samples
blender -b -P models/smg.py -- hero     # only the named camera
```

The raider is grown from an anatomical MakeHuman (MPFB) body. Each garment is a shell taken from the body surface, then inflated, relaxed, trimmed, subdivided, given cloth folds and thickened. It is rigged and ready to animate. It uses MPFB's 53-bone `game_engine` skeleton (`Raider_Skeleton`, UE-style names including fingers). Cloth copies its weights from the body, and hard gear (helmet, respirator, pads, pouches, pack) rides a single bone rigidly. The full build writes:

- `out/raider.glb`: rigged, full detail, about 3M triangles
- `out/raider_game.glb` and `out/raider_game.fbx`: rigged game version without subdivision or fold displacement
- `out/raider_pose.png`: a deformation test pose

All of them are exported in the rest A-pose.

The procedural materials render in Blender (Cycles). `models/game_export.py` bakes them to textures for game engines (below).

## Raider animation

`models/raider_anim.py` keys 30 clips onto `Raider_Skeleton` (run `models/raider.py` first). Every clip is posed by code and baked per frame, so a change to a gait parameter re-bakes the whole set consistently.

- **Weight:** low hips and always-bent knees, chest hunched over the toes, arms held off the body by the gear, a hard hip dip after each footfall, and a torso that trails the hips.
- **Balance:** a centre-of-mass model (body segments, an 11 kg pack, the rifle) is solved every frame. The hips slide until the mass sits over the loaded support: both boots, one boot, the ball of a raised heel, or knee plus toes when kneeling. Weight hands over from boot to boot while walking. The bake log prints the remaining offset per clip.
- **Boots:** planted soles stay flat and don't slide, heels peel over the ball, toes lift on the heel strike, the pushing boot rolls onto its inner edge in strafes, and knees track over the toes.
- **Weapon holds:** shouldered aim, low ready and sprint carry are placed in the chest frame, and both hands are locked to the rifle by two-bone IK (right hand on the pistol grip, left hand under the handguard). The shoulder blade reaches forward when the handguard is out of reach. The rifle rides a `weapon_r` socket bone under `hand_r`; parenting any weapon to it, with no offset, puts it in the hands.

| Clips | Speed (m/s) |
|---|---|
| Idle, Idle_Scan, Crouch_Idle, Fall_Loop | in place |
| Walk / Jog / Sprint | 1.25 / 2.9 / 5.0 |
| Crouch_Walk, Walk_Back, Strafe_L, Strafe_R | 1.0, 1.0, 0.75, 0.75 |
| Rifle_ versions of all of the above, plus Rifle_Aim_Walk | same, Aim_Walk 0.95 |
| Rifle_Idle, Rifle_Aim, Rifle_Fire, Rifle_Reload, Rifle_Crouch_Idle | in place |
| Jump_Start, Jump_Land, Dodge_Roll, Loot, Throw (release at frame 15), Use_Item | one-shot |

```sh
blender -b -P models/raider_anim.py                 # bake, export out/raider_anim.glb/.fbx, preview videos
blender -b -P models/raider_anim.py -- quick        # fast Workbench previews, no export
blender -b -P models/raider_anim.py -- Walk Throw   # only the named clips
blender -b -P models/game_export.py                 # out/game/raider.glb + out/game/<gear>.glb, baked textures
```

Previews go to `out/anim/<clip>.mp4`, plus `out/anim/raider_reel.mp4` with every clip in sequence. All clips are in place (no root motion); move the character controller at the listed speed.
