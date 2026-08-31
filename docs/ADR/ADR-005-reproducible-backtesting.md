# ADR-005: Deterministic and Reproducible Backtesting

**Status:** Accepted  
**Date:** 2026-08-13  
**Owners:** Backtest and Evaluation Team

## Context

Leaderboard chỉ có giá trị khi một kết quả có thể giải thích và chạy lại. Backtest dễ sai do look-ahead, data mutation, implicit defaults, nondeterministic execution hoặc overwrite strategy/scoring behavior.

## Decision

Backtest phải deterministic với complete input. Mỗi run/result lưu:

- Dataset identity, version/checksum và range.
- Strategy/member versions và parameters.
- Initial capital, fees, slippage và position-sizing rules.
- Random seed khi có randomness.
- Execution/schema version.
- Sentiment model version nếu sử dụng.
- Evaluation và scoring policy version.

Engine chỉ đọc market/news data có timestamp không sau decision time. Dataset và StrategyDefinition đã dùng là immutable. Result và evaluation không bị overwrite; thay policy tạo evaluation version mới. Precision, no-trade, zero-loss, zero-variance và NaN semantics phải được định nghĩa trước ranking.

## Alternatives considered

- **Chỉ lưu aggregate metrics:** nhẹ nhưng không giải thích hoặc tái tạo được.
- **Dùng strategy hiện tại khi xem result cũ:** đơn giản nhưng làm lịch sử bị diễn giải lại.
- **Cho phép default ngầm:** giảm input nhưng gây khác kết quả giữa môi trường/version.

## Consequences

### Positive

- Kết quả có thể audit, so sánh và demo lại.
- Giảm look-ahead và ranking không xác định.
- Leaderboard gắn với evidence cụ thể.

### Negative

- Lưu nhiều provenance và version metadata.
- Mọi thay đổi calculation semantics cần version/migration rõ.

## Validation

- Chạy lại cùng complete input tạo equivalent result/checksum.
- Test cố tình đưa future candle/news phải bị từ chối hoặc không được đọc.
- Re-evaluate với policy mới không sửa evaluation cũ.
- Trade/equity curve khớp final equity và aggregate metrics.

## Revisit when

- Hỗ trợ nondeterministic ML strategy cần định nghĩa reproducibility level khác.
- Dataset quá lớn cần immutable snapshot/reference strategy mới.

