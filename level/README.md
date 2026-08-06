# Level manifest

`rootstead_manifest.json` is a read-only snapshot of the `Rootstead` level,
exported from the Unreal editor by `PyTools/export_manifest.py` in the game
project. It exists so agents without editor access can take measurements.

## Why this instead of editor access

The Unreal MCP server binds `127.0.0.1:8000` with **no authentication** and
includes `ProgrammaticToolset`, which runs arbitrary Python inside the editor.
Reaching it from another machine means exposing an unauthenticated
remote-code-execution endpoint, so it stays on loopback.

Concurrency is the second reason. The relay executes snippets on the editor's
**game thread**, one per tick, so two agents cannot interleave mid-script — but
they can still ruin each other: the build scripts destroy every actor with a
given prefix and respawn them, so a second agent holding references to those
actors is left with trashed objects. `save_packages` from one writes whatever
half-finished state the other is in. PIE is exclusive. And a 120 s game-thread
watchdog means a long snippet from one starves the other's into a timeout.

Reading a file has none of those problems.

## Reading it

```
units        1 uu = 1 cm;  +X east, +Y north, +Z up
families     actors grouped by the prefix before the first underscore
```

Families of 40 or fewer are listed actor by actor with location, rotation
(pitch/yaw/roll), scale, world bounds, collision, mesh path and materials.
Larger families give bounds, three sampled actors and the full label list —
6,279 identical vault instances tell you nothing 6,279 times.

## What it is not

A snapshot, not a spec. If it disagrees with a handoff document, the level is
what shipped and the handoff is what was intended; check which one you need
before building against either.

Regenerate on request rather than assuming it is current — `generated_utc` is
in the file.
