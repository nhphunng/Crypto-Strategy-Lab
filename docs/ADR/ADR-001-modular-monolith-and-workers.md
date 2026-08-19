# ADR-001: Modular Monolith with Separate Worker Processes

**Status:** Accepted  
**Date:** 2026-08-13  
**Owners:** Architecture Team

## Context

Crypto Strategy Lab có nhiều nghiệp vụ nhưng nhóm phát triển nhỏ. API và phần lớn use case cần triển khai cùng nhau; backtest lại là công việc nặng CPU và phải scale từ một lên nhiều worker. Microservices từ đầu làm tăng chi phí deployment, tracing, contract management và vận hành mà chưa có số đo chứng minh nhu cầu.

## Decision

Xây backend dưới dạng modular monolith. Các module có boundary rõ nhưng cùng codebase và PostgreSQL. API và Backtest Worker là hai entry point/process riêng dùng chung domain/application code. Worker count thay đổi bằng cấu hình triển khai. Môi trường MVP dùng Docker Compose.

Không dùng Kubernetes, Kafka hoặc tách service/database theo module trong bản đầu. Một deployable mới cần benchmark hoặc operational evidence và ADR riêng.

## Alternatives considered

- **Microservices từ đầu:** scale độc lập tốt nhưng tăng coupling qua network, deployment và observability cost.
- **Một process duy nhất:** đơn giản hơn nhưng backtest nặng có thể chặn API và không chứng minh được worker scaling.
- **Serverless jobs:** giảm vận hành nhưng tăng phụ thuộc nền tảng và làm local demo khó tái tạo.

## Consequences

### Positive

- Development, test và local setup đơn giản.
- Domain code dùng lại giữa API và worker.
- Backtest scale độc lập khỏi API.
- Boundary module tạo đường chuyển sang service riêng nếu sau này cần.

### Negative

- Module isolation dựa nhiều vào quy tắc dependency và test.
- Một database chung cần ownership và migration discipline.
- Không thể scale từng application module độc lập ngoài worker process.

## Validation

- API và worker chạy ở process/container riêng.
- Cùng workload chạy với một và bốn worker cho result set giống nhau.
- Thay worker count không sửa Generator, Evaluator hoặc Leaderboard.
- Architecture test ngăn import trái boundary.

## Revisit when

- Một module cần deployment cadence hoặc scale profile độc lập đã đo được.
- Một failure domain trong monolith gây ảnh hưởng không thể cô lập bằng process/module boundary.
- Database contention trở thành bottleneck có bằng chứng.

