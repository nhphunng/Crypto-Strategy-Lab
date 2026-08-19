# ADR-003: Provider-Neutral Market Data Contract

**Status:** Accepted  
**Date:** 2026-08-13  
**Owners:** Market Data Team

## Context

Frontend, strategy và backtest cùng dùng candle. Nếu các phần này phụ thuộc schema Binance, thêm OKX/Bybit hoặc thay API Binance sẽ buộc sửa nhiều module. Historical và realtime delivery còn có duplicate, out-of-order, incomplete candle và gap sau reconnect.

## Decision

Mọi market source thực hiện `MarketDataProvider` và map payload thành internal `Candle`. Candle identity là:

```text
(provider, pair, timeframe, open_time)
```

Tên nghiệp vụ `openTime` trong SRS ánh xạ sang `open_time` trong backend; đây là cùng một trường định danh.

Quy tắc contract:

- Timestamp lưu UTC; timeframe dùng tập giá trị chuẩn.
- OHLCV được validate trước persistence.
- Phân biệt candle đang mở và đã đóng.
- Duplicate delivery update/ignore cùng logical candle.
- Out-of-order delivery không làm time series đi lùi.
- Dataset dùng cho backtest ghi provider, pair, timeframe, range, completeness và version/checksum.
- Frontend chỉ nhận public REST/WebSocket contract của backend.

Field, precision và endpoint chi tiết được khóa trong Feature 001/002 contracts, không cố định trong ADR này.

## Alternatives considered

- **Dùng trực tiếp Binance DTO:** nhanh ban đầu nhưng tạo provider lock-in.
- **Frontend gọi Binance:** giảm backend work nhưng phá boundary, security và data consistency.
- **Chỉ lưu close price:** đơn giản nhưng không đủ candlestick, indicator và backtest.

## Consequences

### Positive

- Chart, strategy và backtest dùng chung dữ liệu ổn định.
- Có thể thêm provider mới bằng adapter và contract tests.
- Dataset có thể tái sử dụng và audit.

### Negative

- Cần mapper và quy tắc precision/timeframe.
- Provider-specific capability phải biểu diễn qua metadata thay vì rò schema.

## Validation

- Binance và fake provider cùng vượt provider contract test.
- Import cùng range hai lần không tạo duplicate logical candle.
- Reconnect test phát hiện và backfill gap.
- Thêm provider không sửa frontend, Strategy Engine hoặc Backtester.

## Revisit when

- Hỗ trợ dữ liệu không phải candle cần contract khác như order book hoặc trades.
- Nhiều provider có semantics không thể biểu diễn an toàn bằng Candle hiện tại.
