from __future__ import annotations

from typing import cast

import pytest

from crypto_lab.application.chart_delivery.subscription_registry import (
    SlotBinding,
    SubscriptionChange,
    SubscriptionLimitExceeded,
    SubscriptionRegistry,
)
from crypto_lab.domain.market_data.selection import MarketSelection


def selection(timeframe: str) -> MarketSelection:
    return MarketSelection("BINANCE", "BTCUSDT", timeframe)


def test_fifth_slot_rejection_is_atomic_across_bindings_and_reference_counts() -> None:
    registry = SubscriptionRegistry(max_slots=4)
    one_minute = selection("1m")
    five_minutes = selection("5m")
    registry.bind("slot-1", one_minute)
    registry.bind("slot-2", one_minute)
    registry.bind("slot-3", five_minutes)
    registry.bind("slot-4", selection("1h"))
    bindings_before = registry.bindings
    one_minute_slots_before = registry.slots_for(one_minute)
    five_minute_slots_before = registry.slots_for(five_minutes)

    with pytest.raises(SubscriptionLimitExceeded) as caught:
        registry.bind("slot-5", one_minute)

    assert caught.value.code == "MARKET_SUBSCRIPTION_LIMIT_REACHED"
    assert caught.value.limit == 4
    assert registry.slot_count == 4
    assert registry.bindings == bindings_before
    assert registry.binding_for("slot-5") is None
    assert registry.slots_for(one_minute) == one_minute_slots_before
    assert registry.slots_for(five_minutes) == five_minute_slots_before
    assert registry.reference_count(one_minute) == 2


def test_stable_slot_id_survives_replacement_while_registry_is_at_capacity() -> None:
    registry = SubscriptionRegistry(max_slots=4)
    original = selection("5m")
    replacement = selection("4h")
    for slot_id, selected in (
        ("chart-primary", selection("1m")),
        ("chart_02", original),
        ("chart-03", selection("15m")),
        ("chart-04", selection("1h")),
    ):
        registry.bind(slot_id, selected)

    change = registry.bind("chart_02", replacement)

    assert change == SubscriptionChange(
        slot_id="chart_02",
        previous_selection=original,
        selection=replacement,
        acquired_selection=replacement,
        released_selection=original,
        changed=True,
    )
    assert registry.slot_count == 4
    assert registry.binding_for("chart_02") == replacement
    expected_slot_ids = (
        "chart-primary",
        "chart_02",
        "chart-03",
        "chart-04",
    )
    assert tuple(binding.slot_id for binding in registry.bindings) == tuple(
        sorted(expected_slot_ids)
    )


def test_equal_value_selections_share_acquire_and_release_only_on_last_unbind() -> None:
    registry = SubscriptionRegistry()
    first_value = selection("5m")
    equal_value = selection("5m")

    first = registry.bind("slot-1", first_value)
    second = registry.bind("slot-2", equal_value)
    first_unbind = registry.unbind("slot-1")
    last_unbind = registry.unbind("slot-2")

    assert first.acquired_selection == first_value
    assert second.acquired_selection is None
    assert registry.reference_count(first_value) == 0
    assert first_unbind.released_selection is None
    assert last_unbind.released_selection == first_value
    assert registry.slots_for(first_value) == ()


def test_bind_and_unbind_noops_are_idempotent_and_preserve_state() -> None:
    registry = SubscriptionRegistry()
    selected = selection("30m")
    first = registry.bind("slot-1", selected)
    bindings_after_first = registry.bindings

    duplicate = registry.bind("slot-1", selection("30m"))

    assert first.changed is True
    assert duplicate == SubscriptionChange(
        slot_id="slot-1",
        previous_selection=selected,
        selection=selected,
        acquired_selection=None,
        released_selection=None,
        changed=False,
    )
    assert registry.bindings == bindings_after_first
    assert registry.reference_count(selected) == 1

    released = registry.unbind("slot-1")
    duplicate_unbind = registry.unbind("slot-1")

    assert released.released_selection == selected
    assert duplicate_unbind == SubscriptionChange(
        slot_id="slot-1",
        previous_selection=None,
        selection=None,
        acquired_selection=None,
        released_selection=None,
        changed=False,
    )
    assert registry.slot_count == 0


def test_replacement_releases_unique_old_selection_without_reacquiring_shared_target() -> None:
    registry = SubscriptionRegistry()
    old = selection("1m")
    target = selection("1h")
    registry.bind("slot-old", old)
    registry.bind("slot-a", target)
    registry.bind("slot-b", selection("1h"))

    change = registry.bind("slot-old", target)

    assert change.previous_selection == old
    assert change.selection == target
    assert change.released_selection == old
    assert change.acquired_selection is None
    assert registry.reference_count(old) == 0
    assert registry.reference_count(target) == 3
    assert registry.slots_for(target) == ("slot-a", "slot-b", "slot-old")


@pytest.mark.parametrize(
    "slot_id",
    [
        "",
        "-leading-hyphen",
        "_leading-underscore",
        "contains space",
        "contains/slash",
        "a" * 65,
        None,
        7,
    ],
)
def test_invalid_slot_ids_are_rejected_without_mutation(slot_id: object) -> None:
    registry = SubscriptionRegistry()
    selected = selection("5m")
    invalid = cast(str, slot_id)

    with pytest.raises(ValueError, match="slot_id"):
        registry.bind(invalid, selected)
    with pytest.raises(ValueError, match="slot_id"):
        registry.unbind(invalid)

    assert registry.bindings == ()
    assert registry.reference_count(selected) == 0


def test_maximum_length_stable_slot_id_is_preserved_verbatim() -> None:
    registry = SubscriptionRegistry()
    slot_id = "A" + "_-" * 31 + "Z"
    selected = selection("2h")

    registry.bind(slot_id, selected)

    assert len(slot_id) == 64
    assert registry.bindings == (SlotBinding(slot_id=slot_id, selection=selected),)


def test_release_all_returns_each_unique_selection_once_and_clears_both_indexes() -> None:
    registry = SubscriptionRegistry()
    five_minutes = selection("5m")
    one_hour = selection("1h")
    registry.bind("slot-3", one_hour)
    registry.bind("slot-1", five_minutes)
    registry.bind("slot-2", selection("5m"))

    released = registry.release_all()

    assert released == tuple(sorted((five_minutes, one_hour), key=lambda item: item.key))
    assert registry.slot_count == 0
    assert registry.bindings == ()
    assert registry.binding_for("slot-1") is None
    assert registry.slots_for(five_minutes) == ()
    assert registry.reference_count(five_minutes) == 0
    assert registry.reference_count(one_hour) == 0
    assert registry.release_all() == ()
