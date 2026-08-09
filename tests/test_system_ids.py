from __future__ import annotations

from conftest import DESTINATION_SYSTEM_ID, PluginFixtures

from starforge.core.system_ids import allocator_from_usage, collect_system_id_usage


def test_collect_system_id_usage_reads_synthetic_system(plugin_fixtures: PluginFixtures) -> None:
    usage = collect_system_id_usage([plugin_fixtures.destination])
    system_ids = {item.system_id for item in usage}
    assert DESTINATION_SYSTEM_ID in system_ids


def test_allocator_skips_existing_ids(plugin_fixtures: PluginFixtures) -> None:
    usage = collect_system_id_usage([plugin_fixtures.source, plugin_fixtures.destination])
    allocator = allocator_from_usage(usage)
    generated = allocator.allocate_random()
    assert generated not in {item.system_id for item in usage}
