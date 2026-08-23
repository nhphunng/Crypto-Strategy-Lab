# ADR-004: Strategy Contract, Registry, and Immutable Versions

**Status:** Accepted  
**Date:** 2026-08-13  
**Owners:** Strategy Team
**Extended by:** [ADR-006](ADR-006-llm-generated-strategy-isolation.md) for LLM-generated artifact validation and execution

## Context

Hệ thống phải thêm MA, RSI, Bollinger, Support/Resistance, MACD và News Sentiment mà không sửa Backtester, Evaluator hoặc Leaderboard. Strategy behavior và parameters có thể thay đổi; kết quả cũ vẫn phải chỉ đúng implementation đã dùng.

## Decision

Mọi strategy thực hiện một contract ổn định:

```text
validate(parameters)
analyze(immutable StrategyContext) -> Signal
```

`Signal.action` chỉ nhận `BUY`, `SELL` hoặc `HOLD`. Strategy được đăng ký qua `StrategyRegistry`, kèm type, version và parameter schema. UI và Search đọc registry metadata thay vì hard-code danh sách.

`StrategyDefinition` là immutable và chứa ít nhất `strategy_id`, `strategy_type`, `strategy_version`, `parameters`. Thay logic hoặc parameter set tạo version mới. Composite Strategy dùng cùng contract và lưu exact member versions, weights và resolution policy.

Strategy không truy cập database, queue, HTTP hoặc sentiment model; dữ liệu cần thiết đi qua immutable `StrategyContext` đã căn chỉnh timestamp.

## Alternatives considered

- **If/switch theo strategy name:** dễ bắt đầu nhưng sửa nhiều nơi khi thêm strategy.
- **Unrestricted dynamic code upload:** linh hoạt nhưng tăng rủi ro security và reproducibility; vẫn bị cấm. ADR-006 cho phép riêng LLM-generated artifacts qua review, validation và isolated runtime bắt buộc.
- **Strategy tự tải dữ liệu:** làm implementation tự chủ nhưng phá consistency và testability.

## Consequences

### Positive

- Thêm strategy với phạm vi thay đổi nhỏ.
- Single và Composite Strategy đi chung pipeline.
- Experiment cũ giữ đúng version.

### Negative

- Registry và compatibility validation cần thiết kế rõ.
- Thay contract cần schema/version migration.

## Validation

- Thêm MACD chỉ thêm implementation, registration, metadata và tests.
- Backtester, Evaluator và Leaderboard không có nhánh theo concrete strategy.
- Cùng context/parameters tạo cùng signals.
- Thay strategy behavior tạo version mới và không đổi historical result.

## Revisit when

- Cần mở rộng beyond ADR-006 sandbox policy, ví dụ third-party arbitrary upload hoặc native/GPU capability.
- Strategy contract không đủ cho multi-asset hoặc stateful strategies.
