# Crypto Strategy Lab — Database Migration Rules

**Applies to**: Every PostgreSQL schema or data migration  
**Migration tool**: Alembic  
**Last reviewed**: 2026-08-16

## 1. Objective

These rules allow multiple features to evolve one database without overwriting
tables, losing migration ancestry, or making deployed data uninterpretable.
The target ownership and relationships are defined in
[`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md); merged Alembic revisions remain the
physical source of truth.

## 2. Non-negotiable rules

1. Never edit, rename, reorder, or delete a migration after it has been merged
   or applied to a shared environment.
2. Every schema change is a new Alembic revision. A correction to an existing
   table is another forward migration.
3. Set `down_revision` from the actual integrated Alembic head; never guess it
   from a feature number, timestamp, branch, or task plan.
4. Before merge, the revision graph must have exactly one head unless the PR is
   an explicitly reviewed temporary branch or merge revision.
5. A feature owns only the tables assigned to it in `DATABASE_SCHEMA.md`.
   Cross-owner changes require both owners' review.
6. Do not create a local copy of an upstream table to avoid coordinating a
   foreign key. Land the upstream migration first, then reference it.
7. Autogeneration is a draft. A human must review types, nullability, defaults,
   check/unique constraints, indexes, FK deletion behavior, and downgrade SQL.
8. Test migrations against real PostgreSQL, not only SQLite or mocked
   repositories.
9. Keep ORM mappings, Alembic metadata discovery, and the schema contract in
   the same change as the migration.
10. Application startup must not call `Base.metadata.create_all()` against a
    managed environment. Alembic alone advances shared schemas.

## 3. Ownership policy

| Owner | May create/change without cross-owner approval | Must not own |
|---|---|---|
| Feature 001 | Candle and dataset tables | Realtime session, strategy, backtest, ranking tables |
| Feature 002 | No durable tables in v1 | Candle duplicates or chart/session persistence |
| Feature 003 | `strategy_definitions` | Signals, trades, results, evaluations |
| Feature 004 | Execution/backtest/evaluation tables | Candle, strategy-definition, leaderboard tables |
| Feature 005 | Leaderboard projection and update/outbox tables | Evaluation, Signal, Trade duplicates |

An owner review is required when another feature proposes any of the following:

- adding, dropping, renaming, or changing a column on the owner's table;
- adding a constraint or index that affects owner writes;
- changing FK deletion behavior;
- backfilling, rewriting, or deleting owner data;
- changing an immutable identity, fingerprint, or status lifecycle.

## 4. Revision workflow

### 4.1 Before creating a revision

1. Pull or rebase onto the current integration branch.
2. Read `DATABASE_SCHEMA.md` and the owning feature's `data-model.md`.
3. Confirm the table owner and that no other open work reserves the same table,
   column, constraint, or index name.
4. Confirm the current revision graph:

   ```bash
   alembic current
   alembic heads
   alembic history --verbose
   ```

5. If more than one head already exists, resolve the graph before building a
   dependent feature migration.

### 4.2 Create and review

Generate a revision only after the ORM mapping joins the shared `Base` metadata:

```bash
alembic revision --autogenerate -m "add <feature> <schema change>"
```

Then inspect the generated file line by line. In particular, Alembic may not
correctly infer:

- business check constraints and canonical enum values;
- `JSONB` validation expectations;
- partial, expression, or composite indexes;
- `ON DELETE RESTRICT` versus `CASCADE`;
- safe server defaults and backfill order;
- append-only or idempotency requirements.

Revision IDs must be unique and descriptive. Do not depend on filenames for
ordering; `revision` and `down_revision` define the graph.

### 4.3 Validate locally

Run the migration using a clean PostgreSQL database:

```bash
alembic upgrade head
alembic current
alembic check
```

Also validate an already-populated database at the previous head. A clean
install alone does not prove that upgrades preserve existing data.

Where downgrade is supported and safe, test:

```bash
alembic downgrade -1
alembic upgrade head
```

A destructive downgrade may be intentionally unsupported, but the migration
must fail clearly or document the data-loss boundary. Never pretend a downgrade
is reversible when it discards business records.

### 4.4 Before merge

Rebase or merge the latest integration branch again and run:

```bash
alembic heads
alembic upgrade head
pytest backend/tests/integration/test_migrations.py
```

Expected result: one head, successful upgrade from an empty database, and
successful upgrade from the previous deployed revision.

## 5. Concurrent branches and multiple heads

Two developers can legitimately create revisions from the same parent. Do not
solve the resulting conflict by changing or deleting the other developer's
migration.

Preferred resolution:

1. The later feature rebases onto the newly merged head.
2. If neither revision has reached a shared environment and the later branch is
   private, regenerate or re-parent only that private revision.
3. If both revisions are already merged or shared, create an explicit merge
   revision:

   ```bash
   alembic merge -m "merge concurrent feature heads" <head_a> <head_b>
   ```

4. Put migrations that depend on both branches after the merge revision.
5. Verify `alembic heads` returns one head.

Never change the `down_revision` of an already shared revision merely to make
the graph look linear. That rewrites history and can strand deployed databases.

## 6. Safe schema-change patterns

### 6.1 Add a required column

Use an expand/backfill/contract sequence:

1. Add the column as nullable or with a safe temporary server default.
2. Deploy code capable of reading old and new rows.
3. Backfill in bounded, restartable batches with observable progress.
4. Add validation/checks and set `NOT NULL` only after verification.
5. Remove any temporary default or compatibility path in a later migration.

Do not add a non-null column without a valid plan for existing rows.

### 6.2 Rename or replace a column

For a live/shared environment:

1. Add the new column.
2. Dual-read or dual-write only for a bounded compatibility window.
3. Backfill and verify equivalence.
4. Move all readers to the new column.
5. Drop the old column in a later release.

An immediate rename is acceptable only before any shared environment contains
the table and must be clearly established in review.

### 6.3 Add a foreign key

1. Ensure the referenced migration is in the current ancestry.
2. Verify all existing values resolve.
3. Index the referencing columns when query/delete behavior needs it.
4. Use `RESTRICT` for immutable provenance by default.
5. Use `CASCADE` only for private aggregate children whose root is legitimately
   deletable.

Cross-feature FKs must never point at a table name that exists only in a plan
or ORM skeleton.

### 6.4 Add indexes and constraints

- Use deterministic project naming conventions.
- Add unique constraints for business identity and idempotency, not merely ORM
  application checks.
- Validate query-driven composite index order with repository queries and
  `EXPLAIN ANALYZE` where performance matters.
- On large live tables, assess locks and use PostgreSQL's online/concurrent
  capabilities through an appropriate non-transactional migration strategy.
- Do not add speculative indexes to every provenance column.

### 6.5 Change immutable data

Completed datasets, strategy definitions, policy versions, backtest results,
evaluation results, and published projection history must not be updated in
place to change their meaning. Introduce a new version/result and migrate
references deliberately. Audit timestamps are not part of content identity.

## 7. Data migration rules

- A data migration must be deterministic, idempotent where retry is possible,
  and safe to resume after interruption.
- Large rewrites run in bounded batches; avoid one transaction that locks an
  entire high-volume table.
- Record or log affected row counts and verify them before enforcing new
  constraints.
- Do not fetch network data or depend on mutable external services from an
  Alembic migration.
- Do not embed production secrets or environment-specific IDs.
- Reference/seed data that affects historical behavior must be explicitly
  versioned. Changing a policy creates a new policy version.
- Migration code must not import changing application-domain behavior whose
  future refactor could alter an old revision. Keep required transformation
  logic stable inside the revision or a migration-only helper with a frozen
  contract.

## 8. ORM and metadata rules

- Every persistence model imports the single shared
  `crypto_lab.infrastructure.persistence.models.Base`.
- Do not introduce a second SQLAlchemy metadata registry.
- Alembic `env.py` must import all implemented model modules before exposing
  `target_metadata`; an unimported model is invisible to autogeneration.
- ORM relationships do not replace database FKs, unique constraints, or checks.
- Application enums and database checks must be updated together.
- A persistence skeleton or model file without a migration does not authorize
  code to query that table.

## 9. CI gates

Every migration pull request must pass these gates on PostgreSQL 16:

1. Upgrade an empty database from base to `head`.
2. Upgrade a fixture/database at the previous head to the new `head`.
3. Assert exactly one Alembic head.
4. Run `alembic check` after all model modules are loaded.
5. Run integration tests for new PK, FK, unique, check, and deletion behavior.
6. Test idempotency and concurrent create-or-resolve paths where applicable.
7. Verify immutable records cannot be semantically overwritten through the
   repository API.
8. Confirm API/repository query plans use required indexes for high-volume
   child tables.

The migration test suite should fail when:

- a new model has no migration;
- a migration has an unknown or divergent parent;
- a required constraint exists only in Python;
- a cross-feature FK targets a table absent at that revision;
- an upgrade leaves more than one head.

## 10. Pull-request checklist

- [ ] The schema change is present in the owning feature's data model.
- [ ] `DATABASE_SCHEMA.md` ownership/status/table contract is updated.
- [ ] The migration has the actual current `down_revision`.
- [ ] No merged/shared revision was modified.
- [ ] ORM mappings use the shared `Base` and are imported by Alembic metadata.
- [ ] Upgrade from empty and previous-head PostgreSQL databases passes.
- [ ] `alembic heads` returns exactly one head.
- [ ] Types, nullability, defaults, checks, uniques, indexes, and FK deletion
      behavior were manually reviewed.
- [ ] Existing rows have a safe backfill/compatibility plan.
- [ ] Downgrade behavior and any data-loss boundary are explicit.
- [ ] Constraint, idempotency, and concurrency integration tests pass.
- [ ] Both owners approved every cross-feature table change.

## 11. Incident and rollback policy

If a migration fails in a shared environment:

1. Stop further application rollout and record the current Alembic revision.
2. Determine whether the DDL transaction rolled back completely.
3. Do not edit the failed revision if any environment may have recorded or
   partially applied it.
4. Prefer a new forward-fix revision for production/shared environments.
5. Use downgrade only when it was tested, preserves required data, and the
   deployment owner approves it.
6. Reconcile `alembic_version`, actual database objects, and application
   compatibility before resuming rollout.

Never manually mark a revision as applied with `alembic stamp` to conceal a
failed migration. Stamping is reserved for an explicitly audited baseline or
recovery procedure where the physical schema has been proven equivalent.
