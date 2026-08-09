# StarForge manual validation

Use this checklist after generating a plugin from a blank or near-blank destination.

## xEdit

1. Open the saved plugin and confirm it loads without fatal parse errors.
2. Check `TES4` and verify required masters are present and not duplicated.
3. Confirm the plugin contains `STDT`, `PNDT`, and `LCTN` groups when the saved output should include them.
4. Inspect cloned star, planet, and moon records and verify:
   - `EDID` and display name are correct
   - system IDs and local IDs are coherent
   - orbit/surface/main `LCTN` records are linked to the expected parent
5. Inspect component payloads on cloned records and confirm the visible full-name and detected Houdini-linked strings reflect the new clone names.

## Creation Kit / in-game follow-up

1. Load the saved plugin with its required masters.
2. Verify the created system appears and the plugin resolves without missing-master warnings.
3. Check cloned planets/moons for sane hierarchy and non-broken location linkage.
4. If biome extraction was enabled, verify the expected `.biom` file exists under `planetdata/biomemaps/`.
5. Sanity-check that orbital edits and inserted planets/moons do not produce obviously broken hierarchy or naming.
