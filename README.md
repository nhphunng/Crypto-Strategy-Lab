# Crypto Strategy Lab

Crypto Strategy Lab là nền tảng nghiên cứu chiến lược giao dịch crypto trên dữ liệu lịch sử và realtime. Hệ thống hỗ trợ quản lý chiến lược, chạy backtest, tìm tổ hợp chiến lược, đánh giá kết quả, xếp hạng và phân tích tin tức.

> Đây là công cụ phân tích và mô phỏng. Hệ thống không đặt lệnh giao dịch thật, không quản lý tài sản và không cam kết lợi nhuận.

## Chức năng chính

- **Market**: Tải nến lịch sử từ Binance và nhận cập nhật realtime qua WebSocket.
- **Strategies**: Quản lý Strategy Definition, cấu hình đã lưu và Generated Strategy khi bật profile bảo mật.
- **Backtests**:
  - `Single Backtest` mô phỏng một chiến lược trên dataset bất biến.
  - `Strategy Search` thử và xếp hạng nhiều tổ hợp chiến lược.
  - `Runs` hiển thị lịch sử các lượt tìm kiếm và kết quả đã lưu.
- **Leaderboard**: Dựng Top-K từ Evaluation Result, cập nhật realtime và hiển thị trade/provenance.
- **News & Sentiment**: Thu thập tin RSS, lưu vào PostgreSQL và cung cấp dữ liệu phân tích cho UI/strategy.

## Công nghệ

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- Frontend: React 19, TypeScript, Vite, TanStack Query, Lightweight Charts.
- Kiểm thử: pytest, Ruff, mypy, Vitest và Playwright.
- Môi trường local: Docker Compose.

## Chạy nhanh bằng Docker

### Yêu cầu

- Git.
- Docker Desktop có Docker Compose.
- Kết nối internet để tải image/package và truy cập các provider công khai.

### 1. Chuẩn bị

```powershell
git clone <repository-url>
cd Crypto-Strategy-Lab
Copy-Item .env.example .env
```

Với Git Bash:

```bash
cp .env.example .env
```

`.env.example` chỉ chứa cấu hình local. Không commit `.env` hoặc bất kỳ secret nào.

### 2. Build và khởi động toàn bộ stack

Chạy tại thư mục gốc của repository:

```powershell
docker compose up --build -d
docker compose ps -a
```

| Dịch vụ | Địa chỉ/trạng thái | Ghi chú |
|---|---|---|
| Frontend | <http://localhost:5173> | Nginx phục vụ React và proxy `/api`, `/ws` |
| API | <http://localhost:8000> | Swagger UI tại `/docs` |
| PostgreSQL | `localhost:55432` | Database local trong Docker volume |
| Migrate | `Exited (0)` | One-shot container; trạng thái này là thành công |

Kiểm tra hệ thống:

```powershell
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8000/health/ready
curl.exe http://localhost:8000/api/v1/market-data/dimensions
docker compose logs migrate
```

Hai health endpoint hợp lệ trả về:

```json
{"status":"UP"}
```

Sau khi pull code có migration hoặc dependency mới, chạy lại:

```powershell
docker compose up --build -d
```

Chỉ khi nghi ngờ cache build bị lỗi mới cần build không dùng cache:

```powershell
docker compose build --no-cache
docker compose up -d
```

### 3. Dừng hệ thống

```powershell
docker compose down
```

Lệnh này giữ dữ liệu PostgreSQL. Không thêm `-v` trừ khi chủ động muốn xóa toàn bộ volume và dữ liệu local.

## Phát triển local

### Backend

Backend yêu cầu Python `3.12.x`:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cd ..
docker compose up -d postgres
cd backend
$env:CSL_DATABASE_URL = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab"
python -m alembic -c alembic.ini upgrade head
python -m uvicorn crypto_lab.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

Giữ API đang chạy rồi mở terminal khác:

```powershell
cd frontend
npm ci
npm run dev
```

Vite chạy tại <http://localhost:5173> và proxy `/api`, `/ws` sang API local. Nếu PowerShell chặn `npm.ps1`, dùng `npm.cmd`, ví dụ:

```powershell
npm.cmd run dev
```

## Generated Strategy

Compose mặc định không nhận LLM secret và sẽ fail closed đối với luồng cần provider thật. Để bật profile Generated Strategy, lưu credential và wrapping key trong `.runtime-secrets/` đã được Git ignore:

```bash
mkdir -p .runtime-secrets
openssl rand -base64 32 > .runtime-secrets/source_encryption_key
# Lưu API key bằng secret manager/editor an toàn vào .runtime-secrets/llm_api_key.
```

Khai báo cấu hình không nhạy cảm và đường dẫn secret file trong `.env`:

```dotenv
CSL_LLM_ENDPOINT=https://provider.example/v1/strategy-generation
CSL_LLM_PROVIDER=approved-provider
CSL_LLM_MODEL_ID=approved-model
CSL_LLM_MODEL_VERSION=provider-version
CSL_LLM_API_KEY_HOST_FILE=.runtime-secrets/llm_api_key
CSL_LLM_DATA_POLICY_CONFIRMED=true
CSL_SOURCE_ENCRYPTION_KEY_HOST_FILE=.runtime-secrets/source_encryption_key
CSL_SOURCE_ENCRYPTION_KEY_ID=deployment-key-v1
```

Chỉ bật `CSL_LLM_DATA_POLICY_CONFIRMED=true` sau khi đã kiểm tra chính sách dữ liệu của provider. Khởi động profile local:

```bash
docker compose -f docker-compose.yml -f docker-compose.generated.yml up --build -d
```

Profile sử dụng sandbox tách biệt, không mount Docker socket của host vào API và không truyền application secret vào tiến trình thực thi strategy. Xem [ADR-006](docs/ADR/ADR-006-llm-generated-strategy-isolation.md) để biết ranh giới bảo mật.

Production dùng file Compose riêng và phải có đủ secret, migration, artifact storage và sandbox readiness:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --wait --wait-timeout 60
```

## News collection

News dùng adapter RSS/Atom phía server và lưu item vào PostgreSQL trước khi phục vụ qua `GET /api/v1/news`. Collector mặc định tắt để local/test không tự gọi feed công khai.

```dotenv
CSL_NEWS_COLLECTION_ENABLED=false
CSL_NEWS_COLLECTION_INTERVAL_SECONDS=900
CSL_NEWS_FEEDS=[{"source":"Cointelegraph","url":"https://cointelegraph.com/rss"}]
```

Chạy collector một lần bằng môi trường backend local:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\collect_news_once.py
```

Lỗi của một provider được cô lập và ghi log; dữ liệu đã lưu cùng các luồng Market/Backtest không phụ thuộc uptime của RSS.

## Chạy kiểm tra

### Frontend

```powershell
cd frontend
npm ci
npm run typecheck
npm run test:unit
npm run build
```

### Backend: lint, typecheck và test không phá hủy dữ liệu

Sau khi cài `backend[dev]`:

```powershell
cd backend
python -m ruff check .
python -m mypy src
python -m pytest tests/unit tests/contract -q
```

Sandbox contract test chỉ chạy container thật khi Docker daemon và image sandbox khả dụng; nếu không, test được skip.

### Backend: toàn bộ suite với database test riêng

Một số integration/migration test có thể truncate bảng hoặc downgrade schema. **Không trỏ test vào database phát triển `crypto_lab`.** Tạo database riêng một lần:

```powershell
docker compose up -d postgres
docker compose exec -T postgres createdb -U crypto_lab crypto_lab_test
```

Nếu database đã tồn tại, bỏ qua lỗi `already exists`. Sau đó, tại thư mục `backend`:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab_test"
$env:CSL_DATABASE_URL = $env:TEST_DATABASE_URL
python -m alembic -c alembic.ini upgrade head
python -m pytest -m "not performance"
```

Phải đặt cả hai biến về cùng database test để fixture và subprocess migration không dùng nhầm database phát triển.

### Full-stack Compose + Playwright

Yêu cầu Python 3.12 với backend dev dependencies, Node.js/npm và Google Chrome:

```powershell
cd <repository-root>
npm ci
npm run test:integration
```

Script sẽ dựng Compose stack, migrate, seed dữ liệu demo, chạy các Playwright scenario ổn định và cuối cùng gọi `docker compose down`. Dữ liệu demo được ghi vào database Compose local nhưng volume không bị xóa.

Giữ stack lại để debug:

```powershell
$env:KEEP_STACK = "1"
npm run test:integration
```

Test kết nối Binance thật được tách khỏi regression gate vì phụ thuộc mạng:

```powershell
$env:COMPOSE_E2E = "1"
npx playwright test --config=playwright.compose.config.ts tests/e2e/realtime-multi-chart-compose.spec.ts
```

## Cấu trúc repository

```text
Crypto-Strategy-Lab/
├── backend/             # FastAPI, domain/application, persistence, Alembic, tests
├── frontend/            # React application
├── docs/                # Requirement, SRS, architecture, database và ADR
├── specs/               # Spec Kit artifacts theo feature
├── tests/e2e/           # Playwright scenarios
├── scripts/integration/ # Full-stack Compose test runner
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

## Tài liệu thiết kế

1. [Project Requirement](docs/REQUIREMENT.md)
2. [Software Requirements Specification](docs/SRS.md)
3. [Architecture](docs/ARCHITECTURE.md)
4. [Database Schema](docs/DATABASE_SCHEMA.md)
5. [Database Migration Rules](docs/DATABASE_MIGRATION_RULES.md)
6. [ADR Index](docs/ADR/README.md)
7. [Spec Kit team workflow](docs/team-planning/SPECKIT_TEAM_WORKFLOW.md)

## Xử lý lỗi thường gặp

### Migration không hoàn tất

```powershell
docker compose ps -a
docker compose logs migrate
```

`migrate` ở trạng thái `Exited (0)` là thành công. Exit code khác `0` phải được xử lý trước vì API phụ thuộc migration hoàn tất.

### API chưa ready

```powershell
docker compose logs api
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8000/health/ready
```

### Port bị trùng

Đổi port tương ứng trong `.env`:

```dotenv
CSL_POSTGRES_PORT=55433
CSL_API_PORT=8001
CSL_FRONTEND_PORT=5174
```

Nếu backend chạy ngoài Docker, cập nhật `CSL_DATABASE_URL` theo port PostgreSQL mới.
