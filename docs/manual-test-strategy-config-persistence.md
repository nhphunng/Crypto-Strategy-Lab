# Test thủ công — Strategy Configuration Persistence

> Branch: `feat/strategy-config-persistence`
> Backend: `http://127.0.0.1:8000` (Docker: `docker compose up -d postgres` → `docker compose run --rm migrate` → `docker compose up -d --build api`)
> Frontend: `http://127.0.0.1:5173` (npm run dev) — Vite proxy `/api` → `127.0.0.1:8000`

---

## 1. Chuẩn bị

```bash
# Backend
docker compose up -d postgres
docker compose run --rm migrate        # đã gồm migration 009 (saved_strategy_configurations)
docker compose up -d --build api

# Frontend (terminal riêng)
cd frontend && npm install && npm run dev
```

Mở `http://127.0.0.1:5173`. Bảng migration mới có 2 bảng:
- `saved_strategy_configurations`
- `saved_strategy_configuration_members`

---

## 2. Test LƯU config (nút "Save Strategy") — single

1. Vào **Strategies**.
2. Chọn **MA Cross** (1 method → single, Combine bị bỏ qua).
3. Sang bước **Configure**, chỉnh `period = 34`.
4. Sang bước **Review & Test**, bấm **Save Strategy**.

Kỳ vọng:
- Hiện toast `Saved MA · version 1` (không còn chỉ hiển thị toast suông bên dưới).
- Backend thật đã ghi bảng. Kiểm tra bằng API:

```bash
curl -sS http://127.0.0.1:8000/api/v1/strategy-configurations | python -m json.tool
# data.configurations[0].kind == "SINGLE", members[0].parameters.period == 34,
# selection.pair/timeframe khớp market đang chọn
```

---

## 3. Test HANDOFF Strategies → Backtests (nút "Run Backtest")

1. Từ bước **Review** của config trên, bấm **Run Backtest**.
2. Ứng dụng tự chuyển sang trang **Backtests**.

Kỳ vọng:
- URL có `?configurationId=<uuid>`.
- Dropdown **Strategy** hiển thị `MA · config v1` (kind hiển thị như một entry có prefix saved).
- **Pair** và **Timeframe** được prefill đúng theo config đã lưu (ví dụ SOLUSDT · 1h).
- Các ô **parameters** (đã chọn `period = 34`) được prefill và **khoá** (disabled) — vì bạn đang chạy đúng một bản immutable.

---

## 4. Test composite LƯU + backtest đúng (weighted)

1. Vào **Strategies**, bước **Combine**: chọn **MA Cross** + **RSI Reversal**, chọn **Weighted**.
2. Đặt weights sao cho tổng **đúng 1** (ví dụ 60 / 40). Lưu ý: nếu tổng khác 1, API sẽ trả `422` — đây là hành vi đúng của validation.
3. Sang **Review & Test**, bấm **Save Strategy** (hoặc **Run Backtest**).

Kỳ vọng:
- Toast `Saved MA + RSI · Weighted · version 1`.
- Backend lưu `kind == "COMPOSITE"`, mỗi member có `weight`, `combination.method == "WEIGHTED"`.
- Khi **Run Backtest**, trang **Backtests** nhận `?configurationId`, prefill pair/timeframe, và khi **Run Backtest** chạy thật trên backend với **composite executor** (không phải chỉ 1 strategy).

Xác minh bằng API (thay id vừa lấy):

```bash
curl -sS http://127.0.0.1:8000/api/v1/strategy-configurations/<configurationId> | python -m json.tool
```

---

## 5. Test validation chống lỗi

- **Weighted tổng ≠ 1** → POST `/api/v1/strategy-configurations` trả `422` (không lưu). Thử qua UI: đặt weight 60/50 rồi Save → thấy toast lỗi.
- **Single + có combination** → `422`.
- **Composite thiếu combination** → `422`.
- **BNBUSDT** vẫn bị từ chối ở market data (`MARKET_PAIR_UNSUPPORTED`) — không đổi hành vi.

---

## 6. Test composite backtest sinh tín hiệu tổng hợp

Chạy một backtest với root definition của composite:

```bash
# 1. Materialize dataset
curl -sS -X POST http://127.0.0.1:8000/api/v1/market-data/datasets -H 'Content-Type: application/json' \
  -d '{"schemaVersion":"1","selection":{"provider":"BINANCE","pair":"ETHUSDT","timeframe":"15m"},"range":{"startTime":"2026-08-01T00:00:00.000Z","endTime":"2026-08-08T00:00:00.000Z"}}'

# 2. Lấy configurationId + rootDefinitionId từ bước save
# 3. POST /api/v1/backtest-runs với strategyDefinitionId = rootDefinitionId
# 4. POST /api/v1/backtest-runs/<runId>/start
```

Kỳ vọng trong `start` response: `historyState == "EVALUABLE"`, `signalCount` theo số candle, `tradeCount` > 0, `provenance.strategyId` là `composite-<fingerprint>`.

Nếu chỉ chạy từng member riêng, số trade khác — đây là bằng chứng backend đang **kết hợp tín hiệu** (majority/weighted), không phải dùng một strategy.

---

## 7. Trạng thái đã ghi nhận (mốc xanh)

| Hạng mục | Kết quả |
|---|---|
| Backend pytest (full) | 499 passed, 1 skipped |
| Frontend vitest | 156 passed |
| Frontend typecheck | pass |
| Frontend build | pass |
| Backend ruff | pass |
| Backend mypy (142 files) | pass |
| E2E realtime + market-pair-context | pass |
| E2E leaderboard visualization | fail sẵn có (cần backend ; không do thay đổi này) |

---

## 8. Lưu ý khi test

- Di động lướt từ **SO_L / ETH / SOL / BTC** — đảm bảo backend đang chạy thì dropdown dimentsions mới có đủ 3 pair.
- Tạo lại config nếu DB bị flush bởi bộ integration tests (`run alembic upgrade head` + dọn bảng chạy trên DB dev).
- Lưu ý `configurationVersion` tăng dần theo `configurationKey` (mỗi lần save cùng cấu trúc là một version mới, immutable).

## 9. F5 / refresh — config không còn bị "mất"

Sau khi Save, màn **Strategies** hiện accordion **"Saved strategies · N"** (gọi `GET /api/v1/strategy-configurations` khi mở trang, **mở sẵn**). Vì vậy khi **F5**:

- Config đã lưu vẫn nằm trong DB backend (không mất).
- Accordion liệt kê **5 hàng/trang** (hàng ngang gọn): tên + nhãn SINGLE/COMPOSITE + version + pair · timeframe, nút **Open** / **Backtest**.
- **Phân trang** `‹ 1 2 … ›` khi có nhiều hơn 5 bản.
- Dưới dấu `---` (hoặc) là nút **＋ Add new strategy** → reset wizard về bước 1.

Kiểm tra:
1. Save 1 config → mở lại trang / F5.
2. Accordion "Saved strategies" hiện đúng bản đã lưu (không trắng wizard).
3. Bấm **Open** → wizard điền lại đúng config cũ.
4. Bấm **Backtest** → sang Backtests, prefilled đúng pair/timeframe/params.
5. Nếu > 5 bản: bấm phân trang `2` để xem trang kế.

## 10. Tách màn danh sách vs tạo strategy

Giờ `Strategies` tách thành **2 màn qua route**:
- **`/strategies` (danh sách)** — accordion "Saved strategies · N" + phân trang 5/trang + nút header **"Add new strategy"** (không còn wizard ở đây).
- **`/strategies/new` (tạo)** — wizard đầy đủ (stepper Choose methods → Configure → Combine → Review & Test) + nút **Generate Strategy** + **Strategy Details**. Không còn accordion.

Kiểm tra:
1. Mở `/strategies` → thấy danh sách saved + nút "Add new strategy", **không thấy** stepper/wizard.
2. Bấm **Add new strategy** → chuyển sang `/strategies/new`, wizard bắt đầu bước 1.
3. Ở `/strategies`, bấm **Open** một config → chuyển sang `/strategies/new?configurationId=…`, wizard **hydrate** đúng (market/timeframe/params/method/weights, nhảy tới Combine hoặc Review).
4. Bấm **Backtest** trong danh sách → sang `/backtests` với `?configurationId=`.

> Lưu ý: khi "Open" một composite, wizard nhảy tới bước **Combine**; single thì nhảy tới bước **Review & Test**.

## 11. Tab Runs — lịch sử backtest thật

Giờ tab **Runs** (Backtests › Runs) đọc **`GET /api/v1/backtest-runs`** (phân trang), hiển thị **lịch sử mọi lần chạy backtest** từ backend:

- Mỗi dòng: Run ID, Type `Backtest`, **Strategy** (`strategyId`), **Pair · Timeframe**, **Status** (`REQUESTED/RUNNING/COMPLETED/FAILED`), **Started**, **Completed**, **Seed**, **Failure**.
- Phân trang `‹ Prev / Next ›` (20/trang).
- Khi rỗng: "No backtest runs yet. Run a backtest to see it here."

Kiểm tra:
1. Vào **Backtests › Runs** (bấm tab "Runs").
2. Thấy danh sách các run đã chạy với **đủ số liệu** (strategy, pair/timeframe, trạng thái, thời điểm, seed) — không còn cột toàn '—' nữa.
3. Chạy thêm 1 backtest rồi quay lại Runs → run mới xuất hiện ở đầu.

> Lưu ý: tab **Strategy Search** vẫn là feature riêng (tự tìm tổ hợp), **không** hiện ở Runs; Runs chỉ là lịch sử backtest thật. Tab Runs **không** tự push vào Leaderboard — Leaderboard cập nhật ở bước evaluation.
