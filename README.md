# Crypto Strategy Lab

Crypto Strategy Lab là nền tảng phục vụ nghiên cứu chiến lược giao dịch crypto. Hệ thống thu thập dữ liệu thị trường, hiển thị biểu đồ, mô phỏng chiến lược trên dữ liệu lịch sử và trình bày kết quả phân tích. Hệ thống không gửi lệnh giao dịch thật và không đưa ra cam kết lợi nhuận.

## Trạng thái hiện tại

Repo hiện có backend và frontend chạy được độc lập hoặc cùng nhau bằng Docker Compose:

| Phần | Thư mục | Trạng thái |
|---|---|---|
| Market Data backend | `backend/` | Đã có API lịch sử, WebSocket realtime version 1, subscription sharing, recovery/backfill, PostgreSQL, migration và test |
| Strategy và Backtest/Evaluation | `backend/src/crypto_lab/`, `frontend/src/features/backtests/` | Đã có Strategy Foundation, backtest deterministic, metrics, scoring, comparison, REST API, PostgreSQL schema/repository và Single Backtest frontend integration |
| Leaderboard & Visualization backend | `backend/src/crypto_lab/{domain,application}/leaderboard/` | Đã có Top-K projection, REST snapshot/detail/visualization/trades, WebSocket `LEADERBOARD_UPDATED` |
| Leaderboard & Visualization frontend | `frontend/src/features/leaderboard/` | Đã kết nối API thật: bảng Top-K, live update, chart Buy/Sell + Entry/Exit, trade drill-down |
| News collection Task 3 | `backend/src/crypto_lab/{domain,application,infrastructure}/news/`, `frontend/src/features/news/` | Provider-neutral RSS-first collect/store/API/TanStack Query; `sentiment: null` và `Pending analysis` là deliberate |
| News Sentiment Task 4 | `backend/src/crypto_lab/infrastructure/sentiment/finbert_analyzer.py` | Pinned FinBERT ML inference, versioned analyses, `news_sentiment` strategy, API sentiment filtering and live UI refresh |
| Web frontend | `frontend/` | `/market`, `/backtests` (Single Backtest) và `/leaderboard` đã dùng API thật; Strategy Search, Runs và các màn hình ngoài phạm vi các feature đã tích hợp vẫn dùng adapter mô phỏng |

`frontend/` là vị trí frontend chính thức. Market dashboard, Single Backtest và Leaderboard đã nối backend; Strategy Search/Runs vẫn thuộc các feature queue/search sau.

Backend đang đăng ký các route Market Data, Strategy, Backtest/Evaluation và Leaderboard trong runtime. Leaderboard đọc trực tiếp các Evaluation Result bất biến của Feature 004 và không tự tính lại metric hay score.

## Tiến độ theo implementation plan

Trạng thái được tính từ checkbox trong `specs/*/tasks.md` ngày 2026-08-24:

| Feature | Hoàn thành | Trạng thái hiện tại |
|---|---:|---|
| `001-historical-market-data` | 54/54 | Hoàn thành implementation, test, migration và cross-feature contract |
| `002-realtime-multi-chart` | 58/58 | Hoàn thành code, test, docs, reverse proxy REST/WebSocket, multi-session fan-out, convergence và final analysis gate |
| `003-strategy-foundation` | 91/95 | Đã có strategy contract, registry, built-in/generated strategy flow, persistence, API và test; còn một số validation gate |
| `004-backtest-evaluation` | 72/72 | Hoàn thành deterministic engine, accounting, metrics, scoring, comparison, persistence, REST/frontend integration, reliability, PostgreSQL và convergence gates |
| `005-leaderboard-visualization` | 52/52 | Hoàn thành Top-K projection, live update, visualization, test, k6 và E2E |

Tổng theo năm feature chính: **327/331 task, khoảng 99%**. Tỷ lệ này chỉ thể hiện số checkbox, không phải phần trăm effort vì độ lớn mỗi task khác nhau.

Frontend prototype có plan lưu tham khảo tại `docs/archive/frontend-prototype/001-frontend-prototype-system/` và đã hoàn thành **43/43 task**. Feature 002 không còn dựa vào mock adapter của prototype cho Market dashboard.

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

Mở [http://localhost:5173/market](http://localhost:5173/market) để dùng dashboard realtime. Trang này gọi `/api/v1/market-data/candles` và dùng `/ws/v1/market-data`; backend hoặc provider không sẵn sàng sẽ được hiển thị bằng trạng thái `STALE`, `RECONNECTING`, hoặc `ERROR`, không giả làm dữ liệu live.

### 4. Tắt hệ thống

```powershell
docker compose down
```

`docker compose down` giữ lại dữ liệu PostgreSQL. Lệnh `docker compose down -v` xóa cả volume và toàn bộ dữ liệu local; chỉ dùng khi muốn tạo database mới hoàn toàn.

### 5. Bật Generated Strategy an toàn

Profile mặc định không nhận LLM secret và vì vậy fail closed. Để bật User Stories 5–7, lấy
credential thật của provider và tạo một wrapping key 256-bit. Lưu hai giá trị nhạy cảm trong
thư mục `.runtime-secrets/` đã được Git ignore; không đặt giá trị secret trực tiếp trong `.env`:

```bash
mkdir -p .runtime-secrets
openssl rand -base64 32 > .runtime-secrets/source_encryption_key
# Lưu provider API key vào .runtime-secrets/llm_api_key bằng secret manager/editor an toàn.
```

File `.env` chỉ chứa cấu hình không nhạy cảm và đường dẫn tới hai secret file. Không commit, log,
đưa secret xuống browser, hoặc sao chép chúng vào source/test fixture:

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

Chỉ đặt `CSL_LLM_DATA_POLICY_CONFIRMED=true` sau khi provider bảo đảm nội dung không được dùng để
training và dùng retention tối thiểu theo security policy. Khởi động secure profile:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.generated.yml \
  up --build -d
```

Compose mount hai secret thành file chỉ đọc trong trusted API process. Profile vẫn dùng volume artifact mã
hóa mode `0700` và một Docker daemon chuyên biệt không chứa application secrets. API không mount
Docker socket của host; mỗi sandbox invocation nhận `Env: []` và vẫn là ephemeral, non-root,
networkless, read-only, capability-free, resource-bounded theo ADR-006.

Production dùng duy nhất file Compose production; startup và CD sẽ fail nếu thiếu secret file,
cấu hình LLM, migration, artifact storage, hoặc sandbox readiness:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  up -d --wait --wait-timeout 60
```

Trong lần deploy chuyển đổi, CD tạo các file trên từ hai biến legacy
`CSL_LLM_API_KEY` và `CSL_SOURCE_ENCRYPTION_KEY_BASE64` trong `.env.production` nếu file chưa tồn
tại; giá trị không được in hoặc truyền vào environment của API. Sau lần deploy thành công đầu tiên,
xóa hai biến legacy khỏi `.env.production`; các lần deploy tiếp theo chỉ dùng secret file.

`CSL_LLM_PROVIDER` chọn dialect: chứa `openai`/`gpt` sẽ nói contract OpenAI Chat Completions,
chứa `gemini`/`google` sẽ nói contract Gemini `generateContent`, giá trị khác dùng contract
provider-neutral gốc (dành cho fixture xác định hoặc provider có proxy tương thích). Cả ba đường
đều được implement trực tiếp trong
`backend/src/crypto_lab/infrastructure/llm/strategy_generation_adapter.py`; `CSL_LLM_ENDPOINT` trỏ
thẳng vào API thật của OpenAI/Gemini, không cần proxy.

## News collect → store → API → UI (Task 3)

Theo `docs/REQUIREMENT.md` §§27–28 và ADR-007, News không gắn cứng với một website:

```text
HTTPS RSS/Atom → RSS NewsProvider → CollectNews → NewsRepository
               → PostgreSQL news_items → GET /api/v1/news
               → TanStack Query → /news
```

RSS/Atom là adapter đầu tiên. Adapter khác có thể được thêm sau `NewsProvider` mà không sửa repository, API hoặc frontend. Deduplication dùng unique `(provider, provider_item_id)` và `canonical_url`; `related_coins` có GIN index, còn newest-first pagination dùng `(published_at DESC, id)`.

Collection remains independent of sentiment analysis. The Task 4 worker reads stored articles and writes immutable, versioned `news_sentiment_analyses`. News without a completed analysis of its current content returns `sentiment: null`; completed articles show the actual model label and confidence. The News page refreshes every 15 seconds and supports server-side sentiment filtering, including correct pagination totals.

### Thành's tasks: background search and ML sentiment

Both local and production Compose enable `CSL_SEARCH_LOOP_ENABLED` and
`CSL_SENTIMENT_ANALYSIS_ENABLED`. Search generates new combinations through the
registry and persists them in the same search runs/candidate queue used by manual
Search. One coordinator per configured loop consumes queued candidates, evaluates
them, and feeds the leaderboard. Completed candidates are reused after restart;
the next cycle and progress totals come from stored runs. Background runs appear
in Search/Runs with their backtest and evaluation links. Generation errors remain
visible as failed runs. Its controls are
`GET /api/v1/search-loop/status`, `POST /api/v1/search-loop/pause`, and
`POST /api/v1/search-loop/resume`; pause takes effect between cycles.

Sentiment uses [ProsusAI/FinBERT](https://huggingface.co/ProsusAI/finbert), pinned to
revision `4556d13015211d73dccd3fdd39d39232506f3e43`, with stored release version
`1.0.0+4556d1301521`. The CPU model and tokenizer are bundled during Docker build,
so inference works with a read-only filesystem and no runtime model download.
The first image build requires network access and adds the ML runtime/model size.
Local Python installs can use `backend/requirements.sentiment.lock` after the
runtime dependencies. `backend/scripts/cache_sentiment_model.py <directory>`
downloads the pinned model; `CSL_SENTIMENT_MODEL_PATH` selects that local directory.
Without a local path, the adapter downloads the same pinned revision on first use.

`GET /api/v1/sentiment/status` reports pending/analyzed/failed counts.
`GET /api/v1/news?sentiment=POSITIVE` (also `NEUTRAL` or `NEGATIVE`) filters stored
results. The response also includes `sentimentSummary` counts for all articles
matching the coin/date range, independently of pagination and the sentiment filter.
The UI computes positive/neutral/negative percentages among analyzed articles and
shows the pending count separately.
`backend/scripts/analyze_news_once.py` processes one batch immediately.
The default Compose interval is 60 seconds, with up to 50 articles per batch.
Model loading and inference run off the API event loop. A model loading failure
leaves articles pending for retry. The old lexicon scorer remains only for legacy
tests; application wiring uses FinBERT. `news_sentiment` is registered alongside
MA and RSI and is available to the search generator.

Historical sentiment uses the latest analysis available at each candle's close,
so a later article revision cannot hide the earlier evidence. Model identity,
evidence window and evidence fingerprint participate in signal/context identity
and are stored in each backtest's `sentiment_provenance`; result API responses
expose them as `provenance.sentiment`. Apply Alembic head
`20260903_012_sentiment_search` before running this version; it adds provenance
and background-cycle metadata without rewriting existing runs.

The collection-only Compose E2E fixture explicitly disables both new workers.
For the real ML database regression, run from `backend/` with
`CSL_TEST_FINBERT_PATH` pointing to the cached model and `TEST_DATABASE_URL`
pointing to a **disposable migrated database** (the fixtures clear news, strategy, backtest and leaderboard tables):

```powershell
.venv/Scripts/python.exe -m pytest tests/functional/test_news_sentiment_journey.py tests/functional/test_sentiment_search_journey.py -q
```

The full acceptance test uses actual FinBERT inference and a generated MA + RSI +
Sentiment combination, asserts trades and a ranked evaluation, checks replay
checksums, and exercises background-cycle idempotency through the durable queue.

### Cấu hình collector

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `CSL_NEWS_COLLECTION_ENABLED` | `false` | Bật collection loop; local/test mặc định không gọi mạng |
| `CSL_NEWS_COLLECTION_INTERVAL_SECONDS` | `900` | Khoảng cách giữa hai chu kỳ; loop chạy một lần ngay khi bật |
| `CSL_NEWS_FEEDS` | JSON array | Danh sách `{source,url}` HTTPS do server quản lý |

Ví dụ:

```dotenv
CSL_NEWS_COLLECTION_ENABLED=false
CSL_NEWS_COLLECTION_INTERVAL_SECONDS=900
CSL_NEWS_FEEDS=[{"source":"Cointelegraph","url":"https://cointelegraph.com/rss"}]
```

Lỗi một provider được cô lập và ghi log; stored News, Market, Strategy và technical Backtest không phụ thuộc uptime của RSS. Có thể chạy một lần bằng normal application use case:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\collect_news_once.py
```

One-shot trả non-zero chỉ khi mọi provider đã cấu hình đều thất bại.

### Operator/manual smoke checklist

Các bước sau là checklist cần chạy; tài liệu này **không** tuyên bố chúng đã được chạy.

1. Khởi động database, migrate đến head và collect một lần từ HTTPS RSS:

```powershell
docker compose up -d postgres
docker compose run --rm migrate

$env:CSL_DATABASE_URL = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab"
$env:CSL_NEWS_COLLECTION_ENABLED = "false"
$env:CSL_NEWS_COLLECTION_INTERVAL_SECONDS = "900"
$env:CSL_NEWS_FEEDS = '[{"source":"Cointelegraph","url":"https://cointelegraph.com/rss"}]'
backend\.venv\Scripts\python.exe backend\scripts\collect_news_once.py
```

2. Khởi động API/frontend và đọc persisted News:

```powershell
docker compose up -d --build api frontend
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8000/health/ready
curl.exe "http://localhost:8000/api/v1/news?coin=BTC&page=1&pageSize=50"
```

Mở API docs tại [http://localhost:8000/docs](http://localhost:8000/docs) và News UI tại [http://localhost:5173/news](http://localhost:5173/news). Xác nhận headline/source/published time/related coins khớp API; ghi lại một `newsId`/headline, nhấn **F5**, và xác nhận item vẫn còn từ PostgreSQL. UI hiển thị `Pending analysis` trước khi worker hoàn thành, sau đó hiển thị label/score thật từ FinBERT; không hiển thị model/score giả.

3. Kiểm tra degraded isolation mà không xóa volume/database:

```powershell
$env:CSL_NEWS_COLLECTION_ENABLED = "true"
$env:CSL_NEWS_COLLECTION_INTERVAL_SECONDS = "60"
$env:CSL_NEWS_FEEDS = '[{"source":"Broken feed","url":"https://example.invalid/rss"}]'
docker compose up -d --force-recreate api
docker compose logs --since=2m api

curl.exe http://localhost:8000/health/live
curl.exe "http://localhost:8000/api/v1/news?coin=BTC&page=1&pageSize=50"
```

Mở và nhấn **F5** tại [News](http://localhost:5173/news), [Market](http://localhost:5173/market) và [Backtests](http://localhost:5173/backtests). Xác nhận log có News provider error nhưng API vẫn live, stored `newsId`/headline vẫn đọc được, Market/Backtests không bị News exception kéo sập, và không có sentiment giả trong degraded state.

Nếu one-shot chỉ có provider hỏng, exit code non-zero là expected vì mọi provider fail; điều đó không đồng nghĩa API/Market/Backtest bị lỗi.

## Leaderboard và trực quan hóa giao dịch (feature 005)

Leaderboard xếp hạng Top-K từ các `EvaluationResult` bất biến theo `ScoringPolicy` có version, rồi giải thích từng kết quả bằng Candle, Signal và Trade đã ghi nhận. Toàn bộ dữ liệu là mô phỏng lịch sử, không phải lời khuyên đầu tư.

### Luồng API và sự kiện

```text
EvaluationResult (bất biến)
  -> UpdateLeaderboard  : khóa projection, xếp hạng lại, tăng projectionVersion khi có thay đổi
  -> leaderboard_update_records (outbox bền vững)
  -> dispatcher         -> WS /ws/v1/leaderboards : LEADERBOARD_UPDATED v1
  -> REST snapshot      : GET /api/v1/leaderboards  (nguồn dữ liệu có thẩm quyền)
```

Frontend gọi API trên cùng origin và dựa vào Vite dev proxy (hoặc nginx trong Compose) để chuyển tiếp `/api` và `/ws`, giống feature 002. Chỉ đặt `VITE_API_BASE_URL` khi gọi API ở origin khác.

| Endpoint | Mục đích |
|---|---|
| `GET /api/v1/leaderboards` | Snapshot Top-K hiện tại kèm metric, direction/unit, provenance và phân trang |
| `GET /api/v1/leaderboards/{leaderboardId}/entries/{evaluationResultId}` | Provenance đầy đủ và trạng thái sẵn sàng của dữ liệu trực quan |
| `.../visualization?startTime=&endTime=` | Candle, overlay chung, marker BUY/SELL/HOLD/ENTRY/EXIT trong khoảng đã giới hạn |
| `.../trades?page=&pageSize=&sortBy=&sortDirection=` | Danh sách Trade mô phỏng có phân trang và sắp xếp |
| `WS /ws/v1/leaderboards` | Đăng ký theo đúng định danh xếp hạng và nhận `LEADERBOARD_UPDATED` |

Định danh projection gồm phạm vi so sánh (pair, timeframe, runId), `scoringPolicyId`/version, `rankBy` và `k`. Đổi `k` hoặc `rankBy` là một projection khác.

### Tự động chạy evaluation (REQUIREMENT.md §21–§23)

Theo §21, mỗi backtest hoàn tất phải đi vào Leaderboard. Hệ thống làm việc đó theo hai đường:

1. Gọi `POST /api/v1/evaluation-results` — sau khi lưu, evaluation được đưa thẳng vào Leaderboard.
2. Vòng lặp nền (§23): materialize dataset → backtest từng Strategy đã đăng ký → evaluate → rank → Leaderboard, lặp lại theo chu kỳ.

Vòng lặp bật sẵn trong `docker-compose.yml`, tắt mặc định ở môi trường test/local:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `CSL_AUTO_EVALUATION_ENABLED` | `false` (compose: `true`) | Bật vòng lặp |
| `CSL_AUTO_EVALUATION_PAIR` | `BTCUSDT` | Market Pair dùng để backtest |
| `CSL_AUTO_EVALUATION_TIMEFRAME` | `15m` | Timeframe |
| `CSL_AUTO_EVALUATION_CANDLES` | `500` | Số Candle đã đóng trong cửa sổ đánh giá |
| `CSL_AUTO_EVALUATION_INTERVAL_SECONDS` | `3600` | Khoảng cách giữa hai chu kỳ |

Mỗi bước đều idempotent: chạy lại một chu kỳ sẽ dùng lại đúng run/result/evaluation cũ theo định danh bất biến, nên Leaderboard không có dòng trùng và không phát sinh event thừa. Một Strategy lỗi chỉ bị bỏ qua và ghi log, không chặn các Strategy còn lại.

### Chạy demo

```powershell
docker compose up -d postgres
docker compose run --rm migrate
python backend/scripts/seed_leaderboard_demo.py
docker compose up -d api
cd frontend; npm run dev
```

Mở [http://localhost:5173/leaderboard](http://localhost:5173/leaderboard). Để xem cập nhật realtime, giữ trang mở và chạy:

```powershell
python backend/scripts/seed_leaderboard_demo.py --complete
```

Bảng xếp hạng sẽ tăng `projectionVersion` và cập nhật dòng mới mà không cần refresh. Bấm vào một dòng để mở chart, marker và bảng Trade kèm provenance.

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

Chạy browser acceptance từ thư mục gốc:

```powershell
F:\nodejs\node.exe node_modules/@playwright/test/cli.js test tests/e2e/realtime-multi-chart.spec.ts --project=chromium
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

`backend/tests/functional/` chứa các test đi theo hành trình người dùng thật qua nhiều endpoint (ví dụ: xem snapshot leaderboard rồi drill-down vào Trades, hoặc materialize dataset rồi phân trang toàn bộ Candle). Test market-data chạy với repository/provider giả lập nên không cần database; test leaderboard cần cùng `TEST_DATABASE_URL` ở trên:

```powershell
pytest backend/tests/functional -q
```

### Integration (frontend + backend)

Kiểm tra toàn bộ stack thật — PostgreSQL, migration, API và frontend chạy bằng Docker Compose, dữ liệu leaderboard demo được seed, rồi chạy Playwright qua reverse proxy thật — bằng một lệnh duy nhất tại thư mục gốc:

```powershell
npm ci
npm run test:integration
```

Lệnh này tự động hoá đúng chuỗi bước thủ công ở mục "Chạy demo" phía trên: `docker compose up -d postgres` → chờ healthy → `docker compose run --rm migrate` → `python backend/scripts/seed_leaderboard_demo.py` → `docker compose up -d --build api frontend` → chờ `/health/ready` và frontend sẵn sàng → `playwright test --config=playwright.compose.config.ts` (chạy `leaderboard-visualization.spec.ts` và `realtime-multi-chart.spec.ts`). Stack luôn được tắt bằng `docker compose down` sau khi chạy xong, kể cả khi có lỗi; đặt `KEEP_STACK=1` nếu muốn giữ lại để debug local. Yêu cầu Python `3.12.x` với `backend[dev]` đã cài (xem mục Backend phía trên) và Google Chrome cài trên máy (Playwright dùng `channel: "chrome"`).

Runner tắt các worker nền auto-evaluation, strategy search, sentiment analysis và news collection trong stack kiểm thử để dữ liệu seed không thay đổi giữa các bước. News demo giữ trạng thái `Pending analysis`; cấu hình Compose dùng để chạy ứng dụng bình thường không bị thay đổi.

`realtime-multi-chart-compose.spec.ts` không nằm trong lệnh trên: test này đi qua kết nối WebSocket/REST thật của API tới Binance, và nhiều mạng CI (bao gồm GitHub-hosted runner) không kết nối ổn định tới endpoint công khai của Binance, nên không phù hợp làm cổng regression bắt buộc. Chạy thủ công khi có mạng kết nối được tới Binance:

```powershell
$env:COMPOSE_E2E = "1"
npx playwright test --config=playwright.compose.config.ts tests/e2e/realtime-multi-chart-compose.spec.ts
```

## Cấu trúc chính

```text
Crypto-Strategy-Lab/
├── backend/             # FastAPI, domain, persistence, Alembic và backend tests
├── frontend/            # React app; Market dashboard dùng TanStack Query + Lightweight Charts
├── docs/                # Requirement, SRS, Architecture và ADR
├── specs/               # Spec Kit artifacts theo từng feature
├── tests/               # Playwright E2E và k6 realtime load/soak tests
├── scripts/integration/ # Script chạy full-stack Compose + Playwright bằng một lệnh
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
