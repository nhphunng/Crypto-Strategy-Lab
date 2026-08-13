# ADR-002: Layered Boundaries and Ports/Adapters

**Status:** Proposed  
**Date:** 2026-08-13  
**Owners:** Architecture Team

## Context

Đề bài yêu cầu thay Binance, thêm strategy, đổi search generator và scale worker mà ảnh hưởng ít đến code cũ. Nếu domain gọi trực tiếp FastAPI, SQLAlchemy, queue client hoặc provider SDK, các thay đổi hạ tầng sẽ lan vào business logic và làm test phụ thuộc external services.

## Decision

Backend dùng bốn vùng trách nhiệm:

```text
Domain ← Application ← Delivery
   ↑          ↑          ↑
   └──── Infrastructure ─┘
```

- **Domain:** entities, value objects, strategy, backtest, evaluation và search rules thuần.
- **Application:** use cases và ports cho repository, queue, provider và clock.
- **Infrastructure:** PostgreSQL, job queue, Binance, News Provider và Sentiment Analyzer adapters.
- **Delivery:** REST, WebSocket và worker entry points.

External DTO, queue message, persistence model và domain object là contract khác nhau; mapper phải explicit. Domain không import framework hoặc provider SDK.

## Alternatives considered

- **Controller → ORM model trực tiếp:** ít file hơn nhưng làm business rule dính HTTP/database.
- **Repository và service chung cho mọi module:** giảm class ban đầu nhưng ownership mơ hồ và dễ thành God Service.
- **Full Clean Architecture cho mọi use case:** boundary mạnh nhưng có thể tạo abstraction thừa; dự án chỉ tạo port tại external/change boundary thật.

## Consequences

### Positive

- Domain test được không cần network/database.
- External provider và framework thay thế được.
- Trách nhiệm và dependency direction rõ.

### Negative

- Có thêm mapper, DTO và interface.
- Nhóm phải thống nhất ownership để tránh duplicate abstraction.

## Validation

- Static/import tests cấm domain import FastAPI, SQLAlchemy, concrete queue clients và Binance SDK.
- Strategy/backtest unit tests chạy bằng fixtures thuần.
- Adapter contract tests chứng minh provider payload được map đúng internal contract.

## Revisit when

- Boundary tạo nhiều lớp chuyển đổi nhưng không đem lại khả năng test/thay thế.
- Một module cần tách deployable; giữ nguyên ports để giảm migration cost.
