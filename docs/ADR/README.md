# Architecture Decision Records

Thư mục này lưu các quyết định kiến trúc có ảnh hưởng đến nhiều feature của Crypto Strategy Lab.

## Trạng thái

- `Proposed`: đang chờ nhóm review.
- `Accepted`: nhóm đã chấp thuận và các feature plan phải tuân theo.
- `Superseded`: đã được ADR mới thay thế.
- `Deprecated`: không còn áp dụng cho phát triển mới.

## Quy tắc review

1. Mỗi ADR phải nêu rõ vấn đề, quyết định, phương án khác, hệ quả và cách kiểm chứng.
2. ADR chỉ chuyển từ `Proposed` sang `Accepted` sau khi nhóm review.
3. Thay đổi quyết định đã `Accepted` phải tạo ADR mới và đánh dấu ADR cũ là `Superseded`.
4. `plan.md` của feature phải liên kết các ADR liên quan.
5. Chi tiết chỉ thuộc một feature được ghi trong `research.md` hoặc `plan.md`, không cần ADR riêng.

## Danh mục

| ADR | Quyết định | Trạng thái |
|---|---|---|
| [ADR-001](ADR-001-modular-monolith-and-workers.md) | Modular monolith và worker tách process | Accepted |
| [ADR-002](ADR-002-layered-boundaries.md) | Ranh giới Domain, Application, Infrastructure và Delivery | Accepted |
| [ADR-003](ADR-003-normalized-market-data.md) | Market Data Provider và Candle chuẩn hóa | Accepted |
| [ADR-004](ADR-004-strategy-plugin-and-versioning.md) | Strategy contract, registry và version bất biến | Accepted |
| [ADR-005](ADR-005-reproducible-backtesting.md) | Backtest xác định và có thể tái tạo | Accepted |
## Deferred ADRs

Các ADR sau chỉ được tạo khi nhóm bắt đầu feature tương ứng và đã có `spec.md`/`plan.md` draft:

- Queue technology và worker delivery semantics (Redis/Celery hoặc phương án khác).
- Scoring policy, normalization và deterministic tie-breaker.
- Sentiment model/runtime, model revision và failure handling chi tiết.
