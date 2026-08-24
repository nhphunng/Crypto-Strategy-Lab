from __future__ import annotations

import re
from dataclasses import dataclass

from crypto_lab.domain.market_data.selection import MarketSelection

SLOT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class SubscriptionLimitExceeded(ValueError):
    code = "MARKET_SUBSCRIPTION_LIMIT_REACHED"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"A dashboard connection can bind at most {limit} chart slots.")


@dataclass(frozen=True, slots=True)
class SlotBinding:
    slot_id: str
    selection: MarketSelection


@dataclass(frozen=True, slots=True)
class SubscriptionChange:
    slot_id: str
    previous_selection: MarketSelection | None
    selection: MarketSelection | None
    acquired_selection: MarketSelection | None
    released_selection: MarketSelection | None
    changed: bool


class SubscriptionRegistry:
    def __init__(self, *, max_slots: int = 4) -> None:
        if max_slots < 1 or max_slots > 4:
            raise ValueError("max_slots must be between one and four")
        self._max_slots = max_slots
        self._bindings: dict[str, MarketSelection] = {}
        self._selection_slots: dict[MarketSelection, set[str]] = {}

    @property
    def max_slots(self) -> int:
        return self._max_slots

    @property
    def slot_count(self) -> int:
        return len(self._bindings)

    @property
    def bindings(self) -> tuple[SlotBinding, ...]:
        return tuple(
            SlotBinding(slot_id, self._bindings[slot_id]) for slot_id in sorted(self._bindings)
        )

    def binding_for(self, slot_id: str) -> MarketSelection | None:
        return self._bindings.get(slot_id)

    def slots_for(self, selection: MarketSelection) -> tuple[str, ...]:
        return tuple(sorted(self._selection_slots.get(selection, ())))

    def reference_count(self, selection: MarketSelection) -> int:
        return len(self._selection_slots.get(selection, ()))

    def bind(self, slot_id: str, selection: MarketSelection) -> SubscriptionChange:
        self._validate_slot_id(slot_id)
        previous = self._bindings.get(slot_id)
        if previous == selection:
            return SubscriptionChange(slot_id, previous, selection, None, None, False)
        if previous is None and self.slot_count >= self._max_slots:
            raise SubscriptionLimitExceeded(self._max_slots)

        released = self._remove_reference(slot_id, previous) if previous is not None else None
        acquired = selection if self.reference_count(selection) == 0 else None
        self._bindings[slot_id] = selection
        self._selection_slots.setdefault(selection, set()).add(slot_id)
        return SubscriptionChange(slot_id, previous, selection, acquired, released, True)

    def unbind(self, slot_id: str) -> SubscriptionChange:
        self._validate_slot_id(slot_id)
        previous = self._bindings.get(slot_id)
        if previous is None:
            return SubscriptionChange(slot_id, None, None, None, None, False)
        released = self._remove_reference(slot_id, previous)
        return SubscriptionChange(slot_id, previous, None, None, released, True)

    def release_all(self) -> tuple[MarketSelection, ...]:
        released = tuple(sorted(self._selection_slots, key=lambda value: value.key))
        self._bindings.clear()
        self._selection_slots.clear()
        return released

    def _remove_reference(
        self,
        slot_id: str,
        selection: MarketSelection,
    ) -> MarketSelection | None:
        self._bindings.pop(slot_id, None)
        slots = self._selection_slots[selection]
        slots.discard(slot_id)
        if slots:
            return None
        del self._selection_slots[selection]
        return selection

    @staticmethod
    def _validate_slot_id(slot_id: str) -> None:
        if not isinstance(slot_id, str) or SLOT_ID_PATTERN.fullmatch(slot_id) is None:
            raise ValueError("slot_id must be a stable identifier of at most 64 characters")
