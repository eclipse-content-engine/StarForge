# Release process

StarForge releases are built by `.github/workflows/release.yml`; release files
must not be assembled manually.

## Release checklist

1. Confirm CI and the private xEdit, Creation Kit, and in-game matrix pass.
2. Update `src/starforge/__init__.py`, `CHANGELOG.md`, and release docs.
3. Run the Release workflow manually on the candidate commit and install its
   artifacts on a clean supported Windows system.
4. Create and push the annotated tag, for example `v0.3.0-alpha.1`.
5. Verify the GitHub release contains the installer, portable archive, Python
   packages, checksums, and signing-status notice when applicable.
6. Verify both `StarForge.exe` and `starforge-cli.exe --version` after download.

Tag pushes publish a GitHub prerelease candidate from immutable workflow
artifacts. Pull requests that affect packaging run the same build without
publishing a release.

## Optional Windows signing

Configure these GitHub Actions secrets to sign both executables and the
installer:

- `WINDOWS_CERTIFICATE_BASE64`: base64-encoded PFX bytes
- `WINDOWS_CERTIFICATE_PASSWORD`: PFX password

When the certificate is absent, the workflow produces `SIGNING_STATUS.txt` so
the unsigned state is explicit.
