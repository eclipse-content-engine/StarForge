# StarForge manual validation matrix

Synthetic tests validate StarForge's parser/writer contract, but they cannot
substitute for external-tool and game validation. Record the tester, date, tool
version, fixture/output, and evidence link for every row before Phase 5 closes.

| Scenario | xEdit | Creation Kit | In game | Status |
| --- | --- | --- | --- | --- |
| Clone a star into a populated destination | Passed privately | Passed privately | Passed privately | Passed |
| Clone a planet with biome extraction | Passed privately | Passed privately | Passed privately | Passed |
| Clone a moon under an existing planet | Passed privately | Passed privately | Passed privately | Passed |
| Change a star system ID with child locations | Passed privately | Passed privately | Passed privately | Passed |
| Apply each orbit preset and one advanced edit | Passed privately | Passed privately | Passed privately | Passed |
| Recover an autosave and export it | Passed privately | Passed privately | Passed privately | Passed |

Do not mark a row passed without saving the exact generated output and recording
the observed result. Proprietary outputs and game files must remain outside Git.

The repository owner confirmed the complete private matrix on 2026-08-09. Exact
outputs and evidence remain outside the public repository by design.

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

## Validation record

Copy one block per scenario:

```text
Scenario:
Tester and date:
StarForge commit:
xEdit version/result:
Creation Kit version/result:
Game version/result:
Private evidence location:
Notes:
```

### Earlier system-ID output load — partial automated record

```text
Scenario: Change LFIDemoV1 star system ID and preserve child records
Tester and date: Codex automated setup / 2026-08-08
StarForge base commit: 1b05648 plus the Phase 5 working tree
Output SHA-256: B79844AAAD07B9C1984DF693953954ADBD603DC8EDF061E36D01389A9EE95271
xEdit version/result: SF1View 4.1.5o loaded the generated plugin, displayed its
  header and managed groups, and exposed all three planet records. No fatal
  parse error naming the generated plugin appeared before the run was stopped.
Creation Kit version/result: Not run
Game version/result: Not run
Private evidence location: local-only temporary output; not committed
Notes: Full reference construction was stopped after 3m46s. SF1View reported
  definition errors in official SFBGS003 records, unrelated to the generated
  plugin. This is evidence of successful initial parsing, not a completed xEdit
  pass. The temporary copy placed in Starfield/Data was hash-verified and removed.
  This partial record is superseded by the completed private matrix above.
```
