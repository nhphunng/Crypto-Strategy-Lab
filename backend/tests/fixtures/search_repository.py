from types import SimpleNamespace
from uuid import UUID, uuid4


class MemoryRepository:
    def __init__(self) -> None:
        self.run: SimpleNamespace | None = None
        self.items: list[SimpleNamespace] = []
        self.runs: dict[UUID, SimpleNamespace] = {}

    async def create(self, values):
        values = dict(values)
        run_id = values.pop("id", uuid4())
        if run_id in self.runs:
            return self.runs[run_id]
        self.run = SimpleNamespace(
            id=run_id,
            top_score=None,
            top_candidate=None,
            current_candidate=None,
            stop_reason=None,
            failure_detail=None,
            started_at=None,
            completed_at=None,
            **values,
        )
        self.runs[run_id] = self.run
        return self.run

    async def background_runs(self, loop_key):
        return tuple(
            sorted(
                (r for r in self.runs.values() if r.loop_key == loop_key),
                key=lambda r: r.cycle_index,
            )
        )

    async def get(self, run_id):
        return self.runs.get(run_id)

    async def patch(self, run_id, **values):
        for key, value in values.items():
            setattr(self.runs[run_id], key, value)

    async def add_candidate(self, values):
        for existing in self.items:
            if (
                existing.search_run_id == values["search_run_id"]
                and existing.fingerprint == values["fingerprint"]
            ):
                return existing
        item = SimpleNamespace(
            id=uuid4(),
            score=None,
            backtest_run_id=None,
            evaluation_result_id=None,
            failure_code=None,
            completed_at=None,
            **values,
        )
        self.items.append(item)
        return item

    async def candidates(self, run_id, limit=50, sort="recent"):
        return tuple(item for item in self.items if item.search_run_id == run_id)[:limit]

    async def patch_candidate(self, candidate_id, **values):
        item = next(value for value in self.items if value.id == candidate_id)
        for key, value in values.items():
            setattr(item, key, value)

    async def cancel(self, _run_id, _now):
        return False
