# Private compatibility tests

This directory is reserved for opt-in tests against a user's locally installed
game data. Tests here must use the `private_integration` pytest marker, read
paths from `STARFORGE_GAME_DATA`, and skip when that variable is absent.

No plugin, archive, extracted asset, or captured record payload belongs in this
repository.
