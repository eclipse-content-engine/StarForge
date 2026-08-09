# Troubleshooting

## Windows shows a SmartScreen warning

Early alpha builds may be unsigned. Download only from the official GitHub
release, compare the file with `SHA256SUMS.txt`, and read
`SIGNING_STATUS.txt`. Do not bypass a warning if the checksum differs.

## A project will not open

Confirm that each selected plugin exists, is readable, and is not already open
exclusively in another tool. StarForge reports malformed or unsupported input
without modifying it.

## The source template list is empty

Templates must match the body being created: stars use stars, planets use
planets, and moons use moons. Load a source plugin containing the required body
type.

## Biome extraction reports a missing archive

Biome extraction requires the locally owned archive containing the selected
body's data. You can disable extraction and stage the record-only operation, or
provide the archive through project setup. Game archives must never be attached
to a public issue.

## Export is blocked

Resolve every error shown in Review. Warnings can describe limitations that do
not invalidate the output; errors prevent writing. Choose a writable output
directory and never use an input plugin as the output path.

## Recovery is offered after a crash

Read the recovery summary before accepting it. Recovery files are separate from
the protected inputs and remain inert until you explicitly restore them.

## Reporting a problem

Open a GitHub issue with the StarForge version, Windows version, operation,
expected result, and the exact error message. Do not upload Bethesda plugins,
archives, credentials, or other proprietary data. Security vulnerabilities
should be reported using the private process in [SECURITY.md](../SECURITY.md).
