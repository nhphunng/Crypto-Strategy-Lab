# Crypto Strategy Lab

Crypto Strategy Lab là nền tảng phục vụ nghiên cứu chiến lược giao dịch crypto. Hệ thống thu thập dữ liệu thị trường, hiển thị biểu đồ, mô phỏng chiến lược trên dữ liệu lịch sử và trình bày kết quả phân tích. Hệ thống không gửi lệnh giao dịch thật và không đưa ra cam kết lợi nhuận.

## Trạng thái hiện tại

Repo hiện có backend và frontend chạy được độc lập hoặc cùng nhau bằng Docker Compose:

| Phần | Thư mục | Trạng thái |
|---|---|---|
| Market Data backend | `backend/` | Đã có API dữ liệu lịch sử Binance, dataset bất biến, PostgreSQL, migration và test |
| Database features 003–005 | `backend/migrations/` | Đã có schema cho Strategy, Backtest/Evaluation và Leaderboard; application/API tương ứng chưa hoàn chỉnh |
| Web frontend | `frontend/` | Giao diện React prototype đã được hợp nhất vào frontend chính; hiện sử dụng adapter dữ liệu mô phỏng |

`frontend/` là vị trí frontend chính thức. Giao diện đã chạy được nhưng vẫn cần thay mock adapter bằng kết nối backend thật trong các feature tương ứng.

Backend đang đăng ký các route Market Data trong runtime. Các file Backtest/Evaluation/Leaderboard đã có package hoặc persistence foundation nhưng chưa đồng nghĩa với API nghiệp vụ chạy hoàn chỉnh.

## Tiến độ theo implementation plan

Trạng thái được tính từ checkbox trong `specs/*/tasks.md` ngày 2026-08-19:

| Feature | Hoàn thành | Trạng thái hiện tại |
|---|---:|---|
| `001-historical-market-data` | 54/54 | Hoàn thành implementation, test, migration và cross-feature contract |
| `002-realtime-multi-chart` | 0/54 | Spec/plan/tasks đã sẵn sàng; realtime WebSocket và frontend tích hợp chưa implement |
| `003-strategy-foundation` | 2/55 | Đã có Strategy Definition migration và persistence mapping |
| `004-backtest-evaluation` | 4/64 | Đã có package foundation, database mappings và migration |
| `005-leaderboard-visualization` | 3/52 | Đã có package foundation, database mappings và migration |

Tổng theo năm feature chính: **63/279 task, khoảng 23%**. Tỷ lệ này chỉ thể hiện số checkbox, không phải phần trăm effort vì độ lớn mỗi task khác nhau.

Frontend prototype có plan lưu tham khảo tại `docs/archive/frontend-prototype/001-frontend-prototype-system/` và đã hoàn thành **43/43 task**. Đây là bản demo dùng mock adapter, chưa chứng minh các backend feature 002–005 đã hoàn thành.

## Cách chạy nhanh

### Yêu cầu

- Git
- Docker Desktop có Docker Compose
- Node.js `22.22.2` trở lên kèm npm
- Kết nối internet để tải Docker image, npm package và dữ liệu công khai từ Binance

### 1. Clone và chuẩn bị cấu hình

```powershell
git clone <repository-url>
cd Crypto-Strategy-Lab
Copy-Item .env.example .env
```

Các giá trị mặc định trong `.env.example` dùng cho môi trường local và không chứa secret. Không commit file `.env`.

### 2. Bật backend và PostgreSQL

Chạy tại thư mục gốc của repo:

```powershell
docker compose up --build -d
docker compose ps
```

Docker Compose sẽ:

1. Khởi động PostgreSQL tại `localhost:55432`.
2. Chạy Alembic migration.
3. Khởi động API tại `http://localhost:8000`.
4. Build và phục vụ frontend tại `http://localhost:5173`.

Kiểm tra backend:

```powershell
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8000/health/ready
curl.exe http://localhost:8000/api/v1/market-data/dimensions
```

Kết quả health hợp lệ là:

```json
{"status":"UP"}
```

Mở tài liệu API tại [http://localhost:8000/docs](http://localhost:8000/docs).

Xem log khi có lỗi:

```powershell
docker compose logs -f api
```

### 3. Chạy frontend ở chế độ phát triển (tùy chọn)

Frontend đã được bật bởi Docker Compose. Khi cần hot reload để phát triển giao diện, chỉ chạy backend bằng Docker rồi mở terminal thứ hai:

```powershell
docker compose up --build -d postgres migrate api
cd frontend
npm ci
npm run dev
```

Mở [http://localhost:5173](http://localhost:5173).

Giao diện hiện dùng adapter mô phỏng trong `frontend/src/services/mock/`. Vì vậy, frontend vẫn hiển thị dữ liệu demo ngay cả khi chưa kết nối API thật.

### 4. Tắt hệ thống

```powershell
docker compose down
```

`docker compose down` giữ lại dữ liệu PostgreSQL. Lệnh `docker compose down -v` xóa cả volume và toàn bộ dữ liệu local; chỉ dùng khi muốn tạo database mới hoàn toàn.

## Thử API dữ liệu lịch sử

Sau khi backend đạt trạng thái ready:

```powershell
curl.exe "http://localhost:8000/api/v1/market-data/candles?provider=BINANCE&pair=BTCUSDT&timeframe=5m&startTime=2026-08-18T00:00:00Z&endTime=2026-08-18T01:00:00Z&limit=12"
```

API hỗ trợ `BTCUSDT` và các timeframe `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`. Timestamp dùng UTC.

## Chạy kiểm tra

### Frontend

```powershell
cd frontend
npm ci
npm run typecheck
npm run test:unit
npm run build
```

### Backend bằng Python local

Backend yêu cầu Python `3.12.x`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\backend[dev]"
```

Khởi động riêng PostgreSQL, chạy migration và test:

```powershell
docker compose up -d postgres
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/unit backend/tests/contract -q
ruff check backend/src backend/tests
mypy backend/src
```

Các integration test dùng database thật và có thể xóa dữ liệu trong các bảng Candle của database test. Chỉ chạy chúng với database local dùng riêng cho test:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab"
pytest backend/tests/integration -q
```

## Cấu trúc chính

```text
Crypto-Strategy-Lab/
├── backend/             # FastAPI, domain, persistence, Alembic và backend tests
├── frontend/            # Frontend React chính thức; prototype hiện dùng mock adapter
├── docs/                # Requirement, SRS, Architecture và ADR
├── specs/               # Spec Kit artifacts theo từng feature
├── tests/               # E2E/load-test skeleton cấp repo
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

## Quy trình phát triển

Đọc các tài liệu theo thứ tự:

1. [Project Requirement](docs/REQUIREMENT.md)
2. [Software Requirements Specification](docs/SRS.md)
3. [Architecture](docs/ARCHITECTURE.md)
4. [Database Schema](docs/DATABASE_SCHEMA.md)
5. [Database Migration Rules](docs/DATABASE_MIGRATION_RULES.md)
6. [ADR Index](docs/ADR/README.md)
7. [Spec Kit team workflow](docs/team-planning/SPECKIT_TEAM_WORKFLOW.md)

Mỗi feature đi qua:

```text
specify → clarify → plan → checklist → tasks → analyze → implement → converge
```

Không commit `.specify/feature.json`, `.codegraph/`, `.env`, database local hoặc dependency build output.

## Lỗi thường gặp

### Port PostgreSQL `55432` đã được dùng

Đổi port trong `.env`:

```dotenv
CSL_POSTGRES_PORT=55433
```

Nếu chạy backend ngoài Docker, cập nhật `CSL_DATABASE_URL` theo cùng port.

### API chưa ready

```powershell
docker compose ps
docker compose logs migrate
docker compose logs api
```

API chỉ ready sau khi PostgreSQL healthy và migration hoàn tất.

### `npm` không chạy

Kiểm tra:

```powershell
node --version
npm --version
```

Nếu `node` có nhưng `npm` bị thiếu hoặc trỏ sai đường dẫn, cài lại bản Node.js LTS rồi mở terminal mới.

### Muốn dựng lại backend sạch

```powershell
docker compose down
docker compose up --build -d
```

Lệnh trên không xóa database. Chỉ thêm `-v` khi chắc chắn muốn xóa toàn bộ dữ liệu local.
