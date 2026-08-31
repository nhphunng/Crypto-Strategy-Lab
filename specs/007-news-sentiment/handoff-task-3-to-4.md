# Handoff Task 3 → Task 4: News Sentiment

**Ngày:** 2026-08-30
**Task 3 owner:** Nguyễn Hoàng Phi Hùng
**Task 4 owner:** Gia Thành
**Trạng thái:** Task 3 bàn giao contract News collection; Task 4 Sentiment ML + `NewsSentimentStrategy` **chưa hoàn thành**
**Nguồn yêu cầu:** [`docs/REQUIREMENT.md` §§27–30](../../docs/REQUIREMENT.md#27-module-10--news-crawler), [ADR-007](../../docs/ADR/ADR-007-news-provider-pipeline.md)

> Tài liệu này khóa boundary và acceptance gate. Nó không xác nhận các lệnh kiểm thử đã chạy. Chỉ đánh dấu checkbox sau khi có output/evidence thực tế trên branch tích hợp.

## 1. Kết luận bàn giao

Task 3 cung cấp boundary provider-neutral:

```text
RSS/Atom → NewsProvider → CollectNews → NewsRepository
         → PostgreSQL news_items → GET /api/v1/news
         → TanStack Query → News UI
```

Task 3 dừng ở News đã chuẩn hóa và lưu bền vững. Response giữ `sentiment: null`; UI phải hiển thị `Pending analysis`. Không có model, label, score hoặc distribution giả.

Task 4 tiếp tục từ dữ liệu đã lưu. Sentiment Service không được chạy trong crawler, sửa collector để gọi model, hoặc thêm mutable sentiment columns vào `news_items`.

## 2. Contract Task 3 bàn giao cho Task 4

### Domain và persistence

`NewsItem` giữ:

```text
id, provider, provider_item_id,
title, content, source,
published_at, crawled_at,
related_coins, url, canonical_url,
content_fingerprint
```

Identity/deduplication:

- unique `(provider, provider_item_id)` cho item identity tại provider;
- unique `canonical_url` để chống duplicate cross-feed;
- `content_fingerprint = SHA-256(normalized title + content + canonical URL)` làm provenance;
- GIN index `related_coins` cho exact membership;
- B-tree `(published_at DESC, id)` cho pagination xác định.

Task 3 migration head: `20260830_010_news`. `news_items` cố ý không có `sentiment`, `label`, `score`, `model_id` hoặc `model_version`.

### Stable REST shape

Endpoint đọc:

```http
GET /api/v1/news?coin=BTC&publishedAfter=2026-08-23T00:00:00Z&publishedBefore=2026-08-31T00:00:00Z&page=1&pageSize=50
```

Task 3 item:

```json
{
  "newsId": "uuid",
  "title": "Bitcoin ...",
  "content": "RSS summary ...",
  "source": "Cointelegraph",
  "publishedAt": "2026-08-30T12:00:00.000Z",
  "crawledAt": "2026-08-30T12:02:00.000Z",
  "relatedCoins": ["BTC"],
  "url": "https://...",
  "sentiment": null
}
```

Task 4 giữ nguyên endpoint/item fields và chỉ điền reserved object bằng kết quả thật:

```json
{
  "label": "POSITIVE",
  "score": "0.840000",
  "modelId": "finsent",
  "modelVersion": "2.3.0",
  "analyzedAt": "2026-08-30T12:03:00.000Z"
}
```

Không hard-code các giá trị ví dụ trên vào production.

## 3. Kiến trúc bắt buộc của Task 4

### Immutable/versioned persistence

Tạo forward migration sau `20260830_010_news` với bảng riêng:

```text
news_sentiment_analyses
- id UUID PK
- news_id UUID FK news_items(id) ON DELETE CASCADE
- model_id VARCHAR NOT NULL
- model_version VARCHAR NOT NULL
- label VARCHAR NOT NULL: POSITIVE|NEUTRAL|NEGATIVE
- score NUMERIC NOT NULL
- analyzed_at TIMESTAMPTZ NOT NULL
- content_fingerprint CHAR(64) NOT NULL
- status VARCHAR NOT NULL: COMPLETED|FAILED
- failure_code VARCHAR NULL
- UNIQUE(news_id, model_id, model_version, content_fingerprint)
```

Rules:

1. Không update/overwrite analysis lịch sử khi model version hoặc content fingerprint thay đổi.
2. Retry cùng `(news_id, model_id, model_version, content_fingerprint)` phải idempotent.
3. API chỉ project latest `COMPLETED` analysis theo model policy đã chọn; failed/pending không được dựng label.
4. Migration không thêm sentiment columns vào `news_items`.

### Application ports

```python
class SentimentAnalyzer(Protocol):
    model_id: str
    model_version: str

    async def analyze(self, item: NewsItem) -> SentimentPrediction: ...


class SentimentAnalysisRepository(Protocol):
    async def list_pending(
        self, model: ModelRef, limit: int
    ) -> tuple[NewsItem, ...]: ...

    async def save(self, analysis: NewsSentimentAnalysis) -> None: ...

    async def latest_for(
        self, news_ids: tuple[UUID, ...]
    ) -> Mapping[UUID, NewsSentimentAnalysis]: ...
```

Sentiment worker/service đọc stored News và ghi immutable analysis. Crawler/RSS adapter/`CollectNews` không import analyzer và không chờ model inference.

### `NewsSentimentStrategy` boundary

Strategy không đọc repository/database trực tiếp. Tạo application boundary:

```python
class SentimentContextReader(Protocol):
    async def aggregate(
        self,
        pair: str,
        start_time: datetime,
        end_time: datetime,
        model: ModelRef,
    ) -> SentimentAggregate: ...
```

`NewsSentimentStrategy` nhận aggregate qua `StrategyContext` hoặc application adapter, đăng ký bằng `StrategyRegistry` như mọi strategy khác, và không thêm special-case vào Composite/Search/Frontend. Backtest provenance phải giữ model id/version và cửa sổ sentiment để không đọc news tương lai so với decision time.

## 4. Thứ tự implementation đề nghị

1. Chốt `ModelRef`, prediction/analysis domain contracts và failure taxonomy.
2. Tạo migration + repository bất biến; giữ head tuyến tính sau `20260830_010_news`.
3. Cài `SentimentAnalyzer` adapter và bounded batch/worker với failure isolation.
4. Join latest completed analysis trong API read mapper; không sửa collector.
5. Mở frontend sentiment filter/distribution từ API thật; hiển thị analyzed/pending counts.
6. Cài `SentimentContextReader`, đăng ký `news_sentiment`, thêm strategy/composite/backtest provenance tests.
7. Chạy functional journey và degraded/model-version regression trước khi chuyển trạng thái hoàn thành.

## 5. Acceptance gates của Task 4

Tất cả đang để unchecked vì Task 4 chưa hoàn thành:

- [ ] Sentiment Service chỉ consume stored News; crawler không invoke model.
- [ ] Analysis bất biến và versioned theo model + content fingerprint.
- [ ] API trả label/score/model/version/analyzedAt từ persisted analysis thật.
- [ ] Pending/failed analysis vẫn là `sentiment: null`; không có fallback giả.
- [ ] News UI filter/distribution chỉ tính trên analyzed items và hiển thị analyzed/pending counts.
- [ ] Model failure không làm News đã lưu, Market hoặc Backtest unavailable.
- [ ] `GET /api/v1/strategies` discover `news_sentiment` qua Registry bình thường.
- [ ] Search tạo composite chứa `news_sentiment` mà không có frontend business special-case.
- [ ] Backtest không look ahead và provenance giữ sentiment model version.
- [ ] Functional journey `stored News → analyze → API → UI` và strategy contract tests có evidence.

## 6. Operator/manual smoke trước khi nhận Task 4

Chạy tại repository root bằng PowerShell. Đây là checklist cần thực hiện, không phải lịch sử lệnh đã chạy.

### 6.1 Collect, store và read

```powershell
docker compose up -d postgres
docker compose run --rm migrate

$env:CSL_DATABASE_URL = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab"
$env:CSL_NEWS_COLLECTION_ENABLED = "false"
$env:CSL_NEWS_COLLECTION_INTERVAL_SECONDS = "900"
$env:CSL_NEWS_FEEDS = '[{"source":"Cointelegraph","url":"https://cointelegraph.com/rss"}]'
backend\.venv\Scripts\python.exe backend\scripts\collect_news_once.py

docker compose up -d --build api frontend
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8000/health/ready
curl.exe "http://localhost:8000/api/v1/news?coin=BTC&page=1&pageSize=50"
```

Mở:

- API docs: <http://localhost:8000/docs>
- News UI: <http://localhost:5173/news>

Checklist:

- [ ] Headline/source/published time/related coins khớp JSON API, không phải mock.
- [ ] UI hiển thị `Pending analysis`; không có `FinSent-v2.3`, label hoặc score giả.
- [ ] Ghi lại một `newsId`/headline, nhấn **F5**, item vẫn còn vì đọc từ PostgreSQL.

### 6.2 Provider degraded nhưng stored data và module khác vẫn hoạt động

Giữ database/volume, đổi feed sang endpoint HTTPS không phân giải rồi recreate API:

```powershell
$env:CSL_NEWS_COLLECTION_ENABLED = "true"
$env:CSL_NEWS_COLLECTION_INTERVAL_SECONDS = "60"
$env:CSL_NEWS_FEEDS = '[{"source":"Broken feed","url":"https://example.invalid/rss"}]'
docker compose up -d --force-recreate api
docker compose logs --since=2m api

curl.exe http://localhost:8000/health/live
curl.exe "http://localhost:8000/api/v1/news?coin=BTC&page=1&pageSize=50"
```

Mở và nhấn **F5** ở cả ba URL:

- <http://localhost:5173/news>
- <http://localhost:5173/market>
- <http://localhost:5173/backtests>

Checklist:

- [ ] Log ghi lỗi News provider có phân loại nhưng API process vẫn live.
- [ ] Stored headline/`newsId` trước đó vẫn đọc được sau F5.
- [ ] Market và Backtests vẫn mở/hoạt động theo dependency riêng; không bị News exception kéo sập.
- [ ] Không có model/score/label giả xuất hiện trong degraded state.

Nếu one-shot chỉ cấu hình provider hỏng, exit code non-zero là expected vì mọi provider đều fail; đó không phải bằng chứng API/Market/Backtest bị lỗi.

## 7. Evidence phải đính kèm khi hoàn thành

- Alembic heads + migration round-trip output.
- Repository idempotency/model-version tests.
- Analyzer success/timeout/failure-isolation tests.
- API contract output cho pending, completed và failed analysis.
- Frontend unit/typecheck/build output.
- Functional/E2E journey và ảnh/log manual smoke, gồm F5 persistence và provider/model degraded.

Không đổi trạng thái tài liệu thành “Task 4 complete” nếu thiếu bất kỳ gate nào ở trên.
