# Kịch bản thuyết trình — Crypto Strategy Lab

> Bài thuyết trình đồ án cuối kỳ môn **Kiến trúc Phần Mềm** (KTPM).
> Định dạng: HTML (theme `corporate`, layout `centered`) — mở trực tiếp `crypto-strategy-lab-slides.html` trong trình duyệt.
> Phần 4 & 5 dùng **ảnh chụp thật từ hệ thống đang chạy** (`localhost:5173`, capture bằng Playwright; nguồn trong `img/tab-*.png`).
> Phím: `→`/`Space` next · `←` prev · `F` fullscreen · `S` speaker notes.
> Tổng thời lượng dự kiến: ~15 phút · 25 slide.

---

## Phần 1 — Giới thiệu (Slide 1–4)

### Slide 1 · Title — `[~1 phút]`
Chào mọi người. Hôm nay em xin trình bày đồ án cuối kỳ môn **Kiến trúc Phần Mềm**: **Crypto Strategy Lab** — nền tảng phân tích, kết hợp và đánh giá chiến lược giao dịch crypto. Em sẽ đi nhanh và nhấn mạnh vào vấn đề **kiến trúc phần mềm**, vì đó mới là trọng tâm của đồ án.

### Slide 2 · Nội dung — `[~30 giây]`
Buổi thuyết trình gồm sáu phần theo trình tự: giới thiệu đồ án → mục tiêu chính → các thành phần cơ bản → chi tiết từng tab trên web cùng kỹ thuật phía sau → demo và kết quả → kết quả đạt được.

### Slide 3 · Bối cảnh bài toán — `[~1.5 phút]`
Thị trường crypto chạy 24/7, giá được biểu diễn bằng biểu đồ nến. Một cây nến 5 phút gồm **Open, High, Low, Close, Volume**. Trader dùng nhiều chỉ báo kỹ thuật — MA, RSI, Bollinger, Support/Resistance, SMC, Wyckoff — để quyết định mua, bán hoặc đứng ngoài.
[PAUSE] Vấn đề nằm ở chỗ: **không có chiến lược đơn lẻ nào tốt trong mọi điều kiện thị trường.** MA tốt khi có trend nhưng kém khi đi ngang; RSI dễ tạo tín hiệu sai khi trend mạnh.

### Slide 4 · Câu hỏi trung tâm — `[~1 phút]`
Từ đó ta đặt câu hỏi trung tâm: liệu có thể xây một hệ thống cho phép bổ sung nhiều strategy, **tự động kết hợp** thành strategy phức hợp, đánh giá hiệu quả và liên tục tìm ra tổ hợp tốt nhất?
[ASK AUDIENCE] Em nhấn mạnh: đây **không phải** bài toán kiếm tiền, mà là **bài toán kiến trúc phần mềm** — xây nên một nền tảng thử nghiệm có hệ thống.

---

## Phần 2 — Mục tiêu chính (Slide 5–7)

### Slide 5 · Section 02 — `[~15 giây]`
Chuyển sang phần hai: mục tiêu chính. Ở đây em trình bày trọng tâm và cách đo độ hiệu quả của các chiến lược.

### Slide 6 · Trọng tâm: so sánh độ hiệu quả — `[~1.5 phút]`
Mục tiêu cốt lõi là **so sánh độ hiệu quả** giữa các chiến lược một cách có hệ thống, thông qua backtest → metrics → scoring → leaderboard.
Quan trọng là quan niệm đúng: đồ án không nhằm chứng minh MA + RSI kiếm tiền thật, mà là xây nền tảng để **thử nghiệm có hệ thống**. Nhờ đó hôm nay có MA+RSI, ngày mai có thể thêm SMC, Wyckoff hay sentiment mà kiến trúc cũ vẫn hoạt động.

### Slide 7 · Không chỉ đánh giá bằng Profit — `[~1.5 phút]`
Để so sánh công bằng, ta không chỉ nhìn lợi nhuận. Hệ thống đánh giá nhiều chỉ số: **Total Return, Win Rate, Max Drawdown, số giao dịch, Profit Factor, Sharpe.**
[PAUSE] Ví dụ trực quan: Strategy A lời 30% nhưng từng có lúc drawdown 45%; Strategy B lời 25% nhưng drawdown chỉ 8%. Dù A lời hơn, **B ổn định hơn nhiều**. Đây là lý do cần nhiều metric, không chỉ profit.

---

## Phần 3 — Các thành phần cơ bản (Slide 8–10)

### Slide 8 · Section 03 — `[~15 giây]`
Sang phần ba: các thành phần cơ bản của hệ thống, trình bày theo hai lớp: container và quy tắc phụ thuộc.

### Slide 9 · Container — `[~1.5 phút]`
Đây là kiến trúc container. **React Web** giao tiếp với **FastAPI** qua REST và WebSocket. FastAPI gọi các module application + domain. Phía dưới: **PostgreSQL** lưu dữ liệu bền vững, **job queue + background workers** chạy backtest/search nặng, và các **adapter**: Binance cho dữ liệu thị trường, News provider, LLM provider, và cả **sandbox** để chạy strategy sinh tự động.
[KEY POINT] Điểm quan trọng: **frontend không gọi provider, database hay queue trực tiếp** — mọi thứ đi qua backend, backend validate và chuẩn hoá mọi dữ liệu ngoài.

### Slide 10 · Dependency rule — `[~1.5 phút]`
Đây là quy tắc phụ thuộc — cốt lõi để hệ thống mở rộng. Phụ thuộc đi một chiều từ ngoài vào trong:
- **domain**: không import FastAPI, SQLAlchemy, queue hay provider SDK;
- **application**: điều phối use case, chỉ phụ thuộc protocol/interface;
- **infrastructure**: cài đặt adapter (DB, queue, market/news/LLM provider);
- **api/worker**: composition root, không chứa logic indicator, accounting hay scoring.
[KEY POINT] Provider DTO, API DTO, domain object là các **contract riêng**, mapper luôn explicit.

---

## Phần 4 — Từng tab trên web + kỹ thuật (Slide 11–18)

### Slide 11 · Section 04 — `[~20 giây]`
Đây là phần lớn nhất: chi tiết từng tab và kỹ thuật đứng sau. Hệ thống có sáu tab chính.

### Slide 12 · Bản đồ tab — `[~1 phút]`
Sáu tab: **Market** (chart realtime, tối đa 4 khung giờ), **Strategies** (chọn/cấu hình), **Backtests** (mô phỏng giao dịch), **Leaderboard** (xếp hạng + trực quan), **News** (nội dung + sentiment), **Operations** (theo dõi search loop). Em sẽ đi lần lượt, kèm kỹ thuật phía sau.

### Slide 13 · Tab Market + Realtime — `[~2 phút]`
Tab Market hiển thị tối đa **4 chart realtime**, mỗi chart chọn khung giờ riêng, đổi timeframe mà **không reload toàn hệ thống**. Slide có **ảnh chụp thật từ hệ thống**: lưới 2×2 chart BTCUSDT trạng thái Live, OHLCV cập nhật qua WebSocket.
Về kỹ thuật: backend dùng `BinanceRealtimeMarketProvider` mở WebSocket `wss` với URL dạng `pair@kline_5m`, **heartbeat 15s, stale 30s**. Mỗi kline được `map_binance_kline` chuyển thành object `Candle` chuẩn. Khi mất kết nối, provider phát sự kiện **DISCONNECTED** rồi backfill.
[KEY POINT] **Frontend không phụ thuộc cấu trúc dữ liệu Binance** — nhờ adapter, sau này thêm OKX, Bybit, Coinbase mà UI không đổi.

### Slide 14 · Tab Strategies + Registry — `[~2 phút]`
Tab Strategies hiển thị catalog, chọn single/composite, chỉnh tham số. **Ảnh thật** bên phải là danh sách 6 strategy đã lưu trong hệ thống, gồm cả COMPOSITE (MA+RSI, RSI+SARP) và SINGLE (MA, RSI, BBMR) — mỗi mục có phiên bản, pair, timeframe. Về kỹ thuật: mỗi strategy implement một **Protocol `Strategy`** gồm `metadata`, `validate_parameters`, `analyze`. Chiến lược đăng ký vào `StrategyRegistry` qua `register()`, lúc chạy `resolve()` theo id + version.
Hệ thống có sẵn **4 built-in**: MA, RSI, Bollinger, Support/Resistance.
[DEMO] Để thêm MACD chỉ cần viết `class MACDStrategy implements Strategy` rồi gọi `registry.register(MACDStrategy())` — **không sửa controller, backtester, UI, database hay combination engine.**

### Slide 15 · Composite (kết hợp) + `combine_actions` — `[~2 phút]`
Đây là phần trung tâm. **Ảnh thật bên trái là bước Combine trong trình tạo strategy**: chọn Weighted, kéo trọng số Moving Average 60% / RSI 40% (Total 100%), Decision Preview tính weighted score tức thì. Khi các member ra tín hiệu trái ngược (MA bảo mua, RSI bảo bán, SR đứng yên), ta cần quy tắc gộp. Hệ thống hỗ trợ hai phương thức:
- **MAJORITY**: đếm tín hiệu, nhiều nhất thắng, hoà thì theo `tie_action`; biên giao dịch = (BUY − SELL)/n;
- **WEIGHTED**: gán điểm BUY=+1, HOLD=0, SELL=−1, nhân trọng số rồi cộng; score ≥ ngưỡng mua → mua, ≤ ngưỡng bán → bán, còn lại đứng yên. Trọng số phải **cộng bằng đúng 1**.

### Slide 16 · Tab Leaderboard + Scoring — `[~2 phút]`
Tab Leaderboard xếp hạng **Top-K** (1–200), cập nhật live qua sự kiện **LEADERBOARD_UPDATED**, và trực quan hoá giao dịch. **Ảnh thật**: bảng đang có `bollinger v1.0.0` đứng #1 với score 67.37 — chính là kết quả backtest em vừa chạy trên backend (kết nối chuỗi với slide 21).
Kỹ thuật chấm điểm (`score_metrics`): mỗi metric có khoảng `[lower, upper]` và chiều hướng; clamp → chuẩn hoá 0–1 → lộn ngược nếu metric nghịch → nhân trọng số (cộng = 1) → nhân 100.
[KEY POINT] Nhấn chiến lược → chart hiện điểm mua/bán, Entry/Exit, và bảng giao dịch chi tiết.

### Slide 17 · Tab News + Sentiment — `[~2 phút]`
Tab News là pipeline 3 bước: **Collect → Store → Analyze**. **Ảnh thật** của tab News: thanh Sentiment distribution + bảng tin gán nhãn POSITIVE/NEUTRAL/NEGATIVE từng tin. [TRUNG THỰC] Nhắc rõ: dữ liệu tin trong bản demo UI là **mô phỏng**. Mọi nguồn (RSS, News API, crawler) trả về cùng format **`NewsItem`** chuẩn. Sentiment Service phân loại thành **POSITIVE / NEUTRAL / NEGATIVE** kèm điểm.
[KEY POINT] Sentiment không bị buộc vào module crawl, và quan trọng hơn: **sentiment có thể trở thành một Strategy** — ví dụ trung bình sentiment trong 1h > 0.7 → BUY.

### Slide 18 · Tab Operations + Search loop — `[~2 phút]`
Tab Operations theo dõi vòng lặp tìm kiếm và worker. **Ảnh thật**: loop trạng thái RUNNING, pipeline Generate→Backtest→Evaluate→Rank→Improve, 4 worker có progress bar, queue depth, và bảng Dependency Health cho thấy **News Provider DEGRADED nhưng pipeline vẫn chạy** — minh hoạ đúng câu hỏi kiến trúc "News lỗi thì Chart có còn chạy không?". [TRUNG THỰC] Các chỉ số loop/worker trong demo là số mô phỏng của UI. Kỹ thuật: `StrategyGenerator` sinh candidate → backtest → đánh giá → xếp hạng → leaderboard. Bắt buộc có **stop condition**: giới hạn candidate, giới hạn thời gian, hoặc dừng khi không cải thiện sau N iteration — **tránh `while(true)`**.
[KEY POINT] Implementation tốt tách **Generator → Queue → Worker → Eval → Rank**, nhờ đó scale nhiều worker, retry khi lỗi, pause/resume và **thay thuật toán tìm kiếm không đụng code** phía sau.

---

## Phần 5 — Demo & kết quả (Slide 19–22)

### Slide 19 · Section 05 — `[~15 giây]`
Sang phần năm: demo và đọc kết quả thực nghiệm.

### Slide 20 · Kịch bản demo — `[~1.5 phút]`
Đây là kịch bản demo: mở **BTCUSDT** với 4 chart 5m/15m/1h/4h realtime → chọn 4 chiến lược MA/RSI/Bollinger/SR → bấm **START SEARCH** → hệ thống sinh candidate, hiển thị "Candidates: 125 · Backtesting…" → leaderboard tự cập nhật, chiến lược tốt nhất lên đầu bảng. Toàn bộ **không cần refresh** nhờ sự kiện `LEADERBOARD_UPDATED`.

### Slide 21 · Kết quả backtest THẬT — `[~1.5 phút]`
Đây là **kết quả thực nghiệm thật** em vừa chạy trên backend đang hoạt động: chiến lược **Bollinger Bands Mean Reversion v1.0.0**, BTCUSDT 15m, dataset 01→08/08/2026, phí 0.04%, slippage 0.02%.
Số liệu thật: **Return +0.2109% · Win Rate 62.5% (8 lệnh) · Max Drawdown −2.0078% · Sharpe 0.8831 · Profit Factor 1.1847 · Overall Score 67.37** — và chính kết quả này đưa bollinger lên **#1 Leaderboard** (ảnh slide 16). Chart có marker E/X là điểm vào/ra thật của từng lệnh.
[KEY POINT] Nhấn tính **deterministic**: cùng dataset + strategy version luôn cho ra đúng cùng kết quả (result checksum).

### Slide 22 · News/Sentiment — `[~1.5 phút]`
Chuyển sang News. Phân bố sentiment theo UI demo (cửa sổ 7D, model FinSent-v2.3): **60% tích cực, 20% trung lập, 20% tiêu cực** — đúng như thanh Sentiment distribution trên tab News. Sau đó **thêm SentimentStrategy vào search space** và chạy lại loop: MA+RSI+Sentiment, MA+SR+Sentiment. Điều này cho thấy hệ thống **mở rộng sang cả phân tích cảm xúc tin tức**, không chỉ technical analysis.

---

## Phần 6 — Kết quả đạt được (Slide 23–25)

### Slide 23 · Section 06 — `[~15 giây]`
Phần cuối: kết quả đạt được — tiến độ, mức độ hoàn thành và các câu hỏi kiến trúc đã trả lời.

### Slide 24 · Tiến độ 5 feature — `[~1.5 phút]`
Hệ thống chia 5 feature chính, hoàn thành **327/331 task, khoảng 99%**: Market data 54/54, Multi-chart 58/58, Strategy Foundation 91/95, Backtest/Eval 72/72, Leaderboard 52/52. Frontend prototype 43/43.
[TRUNG THỰC] Em muốn nói rõ: tỷ lệ này phản ánh **số checkbox hoàn thành**, không phải phần trăm nỗ lực, vì mỗi task độ lớn khác nhau. Đã đạt được: backtest **deterministic**, realtime ổn định, có integration + E2E test.

### Slide 25 · Trả lời câu hỏi kiến trúc — `[~1.5 phút]`
Tổng kết các câu hỏi kiến trúc trung tâm:
- **Thêm strategy mới?** 1 class `implements Strategy` + 1 dòng `register()`.
- **Random → Genetic search?** Backtester chỉ nhận `CandidateStrategy`, không đổi.
- **Binance → Binance + OKX?** Viết adapter mới, frontend không đổi.
- **100 → 100.000 backtest?** Queue + nhiều Worker.
- **News lỗi, sentiment model đổi?** Chart vẫn chạy, Strategy Engine không bị ảnh hưởng.
- **Kết quả leaderboard thuộc version nào?** Fingerprint + provenance đảm bảo tái lập.

### Slide 26 · Cảm ơn — `[~40 giây]`
Kết luận: Crypto Strategy Lab là một nền tảng thử nghiệm chiến lược có hệ thống, giải quyết trọn vẹn bài toán kiến trúc — mở rộng, thay đổi, quan sát và phát triển lâu dài. Cảm ơn mọi người đã theo dõi. Em sẵn sàng nhận câu hỏi.

---

## Những điểm nhấn cần chú ý khi trình bày

- **Đặt trọng tâm kiến trúc lên trước**, không sa đà vào kết quả trading.
- Nhấn mạnh **"1 class + 1 dòng register"** cho tính mở rộng — đây là minh chứng trực quan nhất.
- Nói rõ **số liệu bảng là minh hoạ** (tránh bị hiểu nhầm là kết quả thật).
- Nêu **stop condition** và **queue/worker** để thể hiện tư duy scalability.
- Khi được hỏi, giải thích **fingerprint + provenance** để chứng minh tính tái lập.
