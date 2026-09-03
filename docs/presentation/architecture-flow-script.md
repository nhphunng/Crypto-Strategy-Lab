# Kịch bản trình bày — Kiến trúc Crypto Strategy Lab

> 1 trang bìa + 15 slide kỹ thuật · Theme Signal Path Atlas · HTML tương tác

## 1. Trang bìa

Em xin trình bày kiến trúc của Crypto Strategy Lab theo đúng đường đi của dữ liệu trong hệ thống: bắt đầu từ Market, đi qua Strategies và Backtests, bổ sung ngữ cảnh từ News, rồi kết thúc ở Leaderboard.

Trọng tâm của phần này không phải là chứng minh một strategy có thể kiếm lợi nhuận thật. Điều nhóm muốn làm rõ là: khi thay nguồn dữ liệu, thêm một strategy mới hoặc chạy lại một experiment cũ, hệ thống có khoanh vùng được thay đổi và vẫn giữ kết quả nhất quán hay không.

Em sẽ bám vào hiện trạng của repo. Thành phần nào đang chạy trong modular monolith thì em trình bày là hiện tại; Queue, worker pool hoặc các cơ chế scale lớn chỉ được nhắc đến như hướng mở rộng, không mô tả như tính năng đã triển khai.

## 2. Slide 1 — Kiến trúc end-to-end

Trước hết là bức tranh end-to-end. Backend được tổ chức theo modular monolith: Market Data, Strategies, Backtests, News và Leaderboard có boundary và trách nhiệm riêng, nhưng vẫn được deploy trong cùng ứng dụng FastAPI. Cách này phù hợp với quy mô đồ án vì nhóm chưa phải vận hành nhiều service độc lập, đồng thời vẫn tránh dồn toàn bộ business logic vào một `TradingService`.

Trình duyệt chỉ giao tiếp qua REST và WebSocket của backend. Binance, RSS/Atom hay các nguồn ngoài đều đi qua adapter; vì vậy DTO của provider không lan thẳng vào UI hoặc domain. PostgreSQL giữ phần state cần tồn tại lâu dài như candle, strategy definition, run, result, news và leaderboard update.

Trade-off là các module vẫn dùng chung process API và database. Boundary trong code giúp maintainability, nhưng chưa tạo fault isolation ở mức hạ tầng. Từ bức tranh này, em đi vào phase đầu tiên là Market—nơi dữ liệu được chuẩn hóa trước khi các module phía sau sử dụng.

## 3. Slide 2 — Dữ liệu thị trường không phụ thuộc Binance

Ở tầng Market, quyết định chính là không để schema Binance trở thành schema của toàn hệ thống. Mỗi nguồn dữ liệu thực hiện `MarketDataProvider`, sau đó map payload riêng về `Candle` nội bộ. Identity của một candle được xác định bằng `provider`, `pair`, `timeframe` và `open_time`; timestamp được quy về UTC, còn OHLCV phải được validate trước khi persistence.

Nhờ contract này, chart, indicator và Backtester cùng đọc một cấu trúc ổn định. Nếu bổ sung OKX hoặc Bybit, nhóm chủ yếu viết adapter, mapper và contract test mới. Frontend hoặc Strategy Engine không cần học thêm DTO riêng của từng sàn.

Đổi lại, hệ thống phải duy trì quy tắc mapping về precision, timeframe và provider-specific capability. Đây là chi phí có chủ đích để tránh provider lock-in. Sau khi đã thống nhất hình dạng của một candle, câu hỏi tiếp theo là làm sao đóng gói dữ liệu lịch sử thành dataset có thể dùng lại và audit.

## 4. Slide 3 — Dataset lịch sử phải tái lập được

Khi người dùng yêu cầu dữ liệu lịch sử, backend không mặc định tải lại toàn bộ range. Market Data Service kiểm tra dữ liệu đã có trong PostgreSQL, xác định gap rồi chỉ gọi provider cho phần còn thiếu. Nếu cùng một range được import lại, logical identity của candle giúp update hoặc bỏ qua duplicate thay vì tạo bản ghi thứ hai.

Dataset phục vụ chart và dataset phục vụ Backtest dùng cùng cấu trúc candle, nhưng mức bảo đảm khác nhau. Chart có thể hiển thị dữ liệu đang hình thành; còn Backtest chỉ nhận dataset đã kiểm tra `completeness`, có range, version và checksum rõ ràng. Checksum ở đây là bằng chứng đầu vào, giúp phát hiện dữ liệu đã thay đổi giữa hai lần chạy.

Nhờ tách dataset khỏi thao tác fetch, Backtester không cần gọi Binance trong lúc mô phỏng. Nó chỉ nhận một snapshot đã xác định. Phần lịch sử như vậy đã ổn định; tiếp theo em chuyển sang nhánh realtime, nơi dữ liệu vẫn liên tục thay đổi nhưng contract đầu ra phải giữ nguyên.

## 5. Slide 4 — Dữ liệu thị trường theo thời gian thực

Với realtime, mỗi chart tile giữ subscription riêng theo `pair` và `timeframe`. Khi mở màn hình, UI lấy snapshot ban đầu qua REST để có dữ liệu vẽ ngay; sau đó WebSocket chỉ đẩy phần cập nhật mới. Cách kết hợp này tránh hai cực đoan: polling liên tục gây dư request, hoặc chỉ dùng WebSocket rồi phải chờ lâu mới có đủ history để vẽ chart.

Ở backend, Subscription Hub quản lý subscriber và có thể dùng chung một upstream stream khi nhiều chart đang xem cùng pair/timeframe. Khi người dùng đổi Chart 1 từ 5m sang 1h, chỉ subscription của tile đó được thay; ba chart còn lại không reload. Đây là lý do multi-timeframe được xử lý theo từng tile thay vì một state chung cho cả màn hình.

Realtime không chỉ là tốc độ đẩy dữ liệu. Hệ thống còn phải nói đúng khi dữ liệu không còn mới. Vì vậy slide tiếp theo tập trung vào tình huống WebSocket bị ngắt và cách bảo toàn chuỗi thời gian sau reconnect.

## 6. Slide 5 — Mất kết nối nhưng không làm mất chuỗi nến

Nếu Binance WebSocket mất kết nối, frontend không nên tiếp tục hiển thị chart như thể dữ liệu vẫn đang live. Backend chuyển connection state để UI có thể báo dữ liệu cũ hoặc đang reconnect. Sau khi kết nối lại, hệ thống không phát ngay candle mới nhất mà dùng historical API để backfill khoảng gap trong thời gian gián đoạn.

Trước khi delivery tiếp tục, dữ liệu đi qua hai guardrail. Duplicate của cùng logical candle được update hoặc ignore; out-of-order message không được làm time series đi ngược. Candle đang mở cũng phải được phân biệt với candle đã đóng, vì update intrabar và một mốc dữ liệu hoàn tất có semantics khác nhau.

Cơ chế này ưu tiên tính liên tục và tính đúng hơn việc chỉ reconnect thật nhanh. Đến đây phase Market đã cung cấp được hai thứ: contract dữ liệu thống nhất và cách phục hồi khi nguồn ngoài không ổn định. Trên nền dữ liệu đó, em chuyển sang Strategies—phần thể hiện rõ nhất khả năng mở rộng của kiến trúc.

## 7. Slide 6 — Thêm strategy mà không sửa toàn bộ hệ thống

Mỗi strategy cùng thực hiện một contract ổn định gồm `validate(parameters)` và `analyze(StrategyContext) -> Signal`. `StrategyRegistry` lưu `type`, `version` và `parameter schema`; UI dùng metadata này để hiển thị cấu hình, còn Search dùng nó để biết strategy nào có thể tham gia search space. Nhờ vậy, danh sách strategy không bị hard-code lại ở nhiều lớp.

Ví dụ khi bổ sung MACD, phạm vi thay đổi mong muốn là implementation, metadata, registration và tests. Backtester chỉ nhận Signal nên không cần thêm `if MACD`; Evaluator và Leaderboard cũng không cần biết công thức MACD. Đây là Strategy Pattern kết hợp Registry/Plugin Architecture ở mức module, không phải cơ chế upload code tùy ý vào process.

Strategy definition là immutable và có version. Khi logic hoặc parameter set thay đổi, hệ thống tạo version mới thay vì overwrite version đã dùng trong experiment cũ. Registry giải quyết câu chuyện mở rộng; slide tiếp theo đi sâu vào boundary bên trong một strategy để giữ implementation đó dễ test và không phụ thuộc hạ tầng.

## 8. Slide 7 — Strategy chỉ phân tích dữ liệu được cấp

`StrategyContext` là đầu vào đã được chuẩn bị sẵn, gồm candles, indicators, timeframe, decision time và sentiment context nếu có. Strategy chỉ phân tích context này rồi trả `BUY`, `SELL` hoặc `HOLD`. Nó không tự gọi HTTP, đọc database, điều khiển Queue hay gọi trực tiếp một sentiment model.

Boundary này ngăn mỗi strategy tự tạo ra một cách truy cập dữ liệu khác nhau. Quan trọng hơn, unit test có thể dựng một context cố định và kiểm tra Signal mà không cần Binance hoặc PostgreSQL. Cùng context và parameters phải tạo cùng kết quả; nếu behavior thay đổi thì version của strategy cũng phải thay đổi.

Warmup được xử lý như một trạng thái có chủ đích. Khi chưa đủ candle để tính MA50 hoặc RSI14, hệ thống trả `HOLD/WARMUP`, không bịa một Signal tạm. Sau khi mỗi strategy đơn lẻ có output thống nhất, hệ thống mới có thể ghép chúng mà không phải viết logic riêng cho từng cặp tổ hợp.

## 9. Slide 8 — Composite Strategy hợp nhất các tín hiệu

Composite Strategy nhận nhiều member strategy nhưng vẫn tuân theo cùng contract đầu ra. Trước khi combine, các Signal phải được align theo timestamp. Nếu một member còn warmup, composite không được lấy Signal của thời điểm khác để bù vào; cấu hình hiện tại giữ kết quả ở `HOLD/WARMUP` cho đến khi đủ điều kiện.

Hệ thống hỗ trợ hai resolution policy. Với `Majority`, action có nhiều phiếu nhất được chọn và tie được xử lý theo cấu hình. Với `Weighted`, `BUY`, `HOLD`, `SELL` lần lượt được encode thành `1`, `0`, `-1`; tổng có trọng số được so với buy/sell threshold. Cùng một indicator vì thế có thể đóng góp khác nhau trong từng composite mà không làm thay đổi Backtester.

Phiên bản hiện tại cho phép cấu hình Weighted, nhưng Random Search đang sinh candidate theo Majority. Đây là giới hạn của search space hiện tại, không phải giới hạn của Composite contract. Khi đã có cách biểu diễn candidate thống nhất, bài toán kế tiếp là chọn và thử nhiều candidate mà vòng lặp vẫn có kiểm soát.

## 10. Slide 9 — Search là một vòng thử nghiệm có kiểm soát

Một Search run bắt đầu từ dataset, tập strategy được phép dùng, kích thước composite, seed và run limit. `RandomSearchGenerator` sinh candidate; mỗi candidate lần lượt đi qua Analyze, Backtest, Evaluate và Rank. Seed được lưu để phần random có thể kiểm soát, còn candidate và progress được persist để giữ lịch sử theo dõi.

Vòng lặp có nhiều stop condition: đạt giới hạn candidate, hết thời gian, không cải thiện sau số iteration quy định, không còn candidate hợp lệ hoặc nhận yêu cầu hủy. Time limit hiện được kiểm tra giữa các candidate, nên nó không cưỡng chế dừng ngay một backtest đang chạy. Nếu một candidate lỗi, lỗi đó được ghi riêng và Search có thể tiếp tục với candidate sau.

Hiện tại việc thực thi và phát progress dùng async task trong process API. Run history được lưu không có nghĩa job đang chạy sẽ tự recovery sau khi API restart. Khi quy mô tăng lên hàng chục nghìn backtest, Durable job store, Queue và worker pool là hướng scale hợp lý; nhưng đó chưa phải deployment hiện tại.

Một caveat khác là `SearchService` vẫn khai báo dependency cụ thể vào `RandomSearchGenerator`. Khi tích hợp generator mới, nhóm còn phải chỉnh type và wiring ở composition root; tuy nhiên Analyze, Backtester và Evaluator không phải viết lại vì các bước phía sau tiếp tục nhận `StrategyCandidate`.

## 11. Slide 10 — Backtest phải deterministic

Backtest chỉ đáng tin khi complete input tạo ra kết quả tương đương ở lần chạy lại. Vì vậy một run không chỉ lưu tên strategy. Nó phải giữ dataset identity và checksum, exact strategy/member versions, parameters, initial capital, fees, slippage, seed, execution policy và scoring policy version.

Các input và result đã dùng được xem là immutable. Nếu nhóm thay công thức strategy hoặc policy đánh giá, version mới tạo result/evaluation mới thay vì sửa lịch sử. Thiết kế này tốn thêm provenance metadata, nhưng đổi lại nhóm có thể giải thích vì sao hai run khác nhau và kiểm tra đúng input đã tạo ra một kết quả.

Guardrail quan trọng nhất là chống look-ahead: tại mỗi decision time, engine chỉ được đọc market/news data đã tồn tại ở thời điểm đó. Future candle hoặc một bài news công bố sau thời điểm ra quyết định không được đi ngược vào context. Sau khi mô phỏng đã deterministic, phần đánh giá được tách riêng để không trộn trading semantics với ranking policy.

## 12. Slide 11 — Đánh giá tách khỏi mô phỏng

Backtester chịu trách nhiệm mô phỏng Signal thành trades và equity curve theo execution settings. Evaluator không chạy lại strategy; nó đọc immutable backtest result rồi tính Return, Win Rate, Max Drawdown, Number of Trades và Sharpe Ratio. Cách tách này cho phép thay scoring policy mà không phải mô phỏng lại giao dịch nếu dữ liệu gốc vẫn phù hợp.

`Balanced v1` dùng Return 35%, Win Rate 25%, Max Drawdown 25% và Sharpe 15%. Các metric được clamp và normalize theo policy trước khi cộng, vì chúng khác đơn vị và khác chiều đánh giá. Return cao là tốt, trong khi Max Drawdown thấp mới là tốt. Trường hợp NaN, zero-trade hoặc zero-variance cũng phải có semantics xác định, không được tự thay bằng một giá trị có lợi cho ranking.

Đây là điểm kết thúc của phase Strategies–Backtests: candidate đã được sinh, mô phỏng và chấm điểm theo một pipeline có thể truy vết. Tuy nhiên dữ liệu đầu vào của hệ thống không chỉ có giá. Tiếp theo em chuyển sang News, một pipeline riêng nhưng vẫn áp dụng cùng nguyên tắc adapter, versioning và fault isolation.

## 13. Slide 12 — News đi qua một contract chung

News áp dụng cùng tư duy provider-neutral như Market Data. `NewsProvider` là port của application; RSS/Atom chỉ là adapter đầu tiên và trả về `CollectedNewsItem` chuẩn hóa. `CollectNews` điều phối các provider, còn `NewsRepository` sở hữu persistence, idempotent upsert và query đã phân trang. Frontend chỉ gọi `GET /api/v1/news`, không đọc RSS trực tiếp.

Pipeline giữ hai lớp identity. `(provider, provider_item_id)` nhận dạng item trong một provider; `canonical_url` chống việc cùng một bài xuất hiện ở nhiều feed rồi tạo nhiều dòng. `content_fingerprint` theo dõi nội dung thay đổi và trở thành provenance cho bước sentiment. Vì vậy fingerprint bổ sung cho identity chứ không thay thế identity.

Lỗi transport, XML hoặc một provider được cô lập để provider khác và chu kỳ sau vẫn chạy. News đã lưu vẫn đọc được khi nguồn ngoài unavailable; đồng thời Market không gọi trực tiếp News nên chart không dừng theo. Sau bước collect–store, sentiment được xử lý thành một phase riêng thay vì gắn model hoặc analyzer vào crawler.

## 14. Slide 13 — Sentiment là một bước xử lý độc lập

Collector và `SentimentAnalyzer` là hai bước độc lập. Collector chỉ chuẩn hóa và lưu News; analyzer đọc các item chưa xử lý rồi tạo result riêng. Nhờ boundary này, lỗi hoặc thay đổi ở sentiment không buộc crawler chạy lại, và việc collect news không phụ thuộc uptime của analyzer.

Hiện trạng repo dùng analyzer dựa trên từ khóa. Mỗi result lưu label, score, analyzer identity/version, `content_fingerprint` và `analyzed_at`. Khi nội dung hoặc version analyzer thay đổi, hệ thống có thể tạo analysis mới mà không overwrite history. Em chỉ mô tả đúng cơ chế đang có, không suy diễn thêm về chất lượng dự báo tài chính của sentiment.

`NewsSentimentStrategy` không đọc thẳng database. Nó nhận aggregate qua context và chỉ được dùng những bài đã publish, đã analyze trước hoặc đúng candle close time. Nếu dữ liệu chưa đủ, strategy trả `HOLD/WARMUP`; quy tắc này tiếp tục chặn look-ahead giống Market Data. Khi các result kỹ thuật và sentiment đều đã có provenance, phase cuối là đưa evaluation result vào Leaderboard để so sánh.

## 15. Slide 14 — Leaderboard là một projection Top-K

Leaderboard là một read projection, không phải nơi chạy lại strategy hoặc Backtest. Nó đọc evaluation result đã lưu, lọc theo scope và eligibility, sau đó sắp xếp để giữ Top-K. Một leaderboard được xác định không chỉ bởi `K`, mà còn bởi comparison scope, scoring policy version và metric dùng để xếp hạng. Tie-breaker có thứ tự cố định để kết quả không thay đổi tùy ý.

Khi projection thay đổi, backend phát `LEADERBOARD_UPDATED` qua WebSocket để UI cập nhật mà không cần refresh. Update record được lưu bền vững và REST có thể tải lại current state sau khi reconnect. Điều này khác với Search progress hiện đang giữ trong memory của process; hai kênh có mức bảo đảm recovery khác nhau và không nên được mô tả như một cơ chế duy nhất.

Leaderboard trả lời câu hỏi “candidate nào đang nằm trong Top-K”, nhưng chưa tự giải thích vì sao. Vì vậy slide cuối đi ngược từ một entry đang hiển thị về evaluation, backtest, strategy version và dataset đã tạo ra nó.

## 16. Slide 15 — Từ hạng #1 truy ngược về bằng chứng

Khi người dùng chọn một entry trên Leaderboard, hệ thống lần theo evaluation result về backtest run, execution settings, strategy definition/member versions và dataset version/checksum. Từ đó UI có thể hiển thị đúng Signals, Trades và Equity Curve gắn với lần chạy đó, thay vì chỉ đưa ra một Overall Score tách rời khỏi nguồn gốc.

Một nguyên tắc rất quan trọng là không dùng version mới nhất của strategy để diễn giải một result cũ. Nếu strategy đã thay đổi từ v1 sang v2, experiment trước đó vẫn phải trỏ đúng v1 và đúng parameters. Tương tự, evaluation policy mới tạo evaluation version mới chứ không overwrite điểm cũ. Nhờ vậy, tên strategy trên Leaderboard không phải bằng chứng duy nhất.

Nhìn lại toàn bộ flow, Market tạo dữ liệu chuẩn và có khả năng phục hồi; Strategies mở rộng qua contract và Registry; Backtests giữ deterministic provenance; News/Sentiment tạo context có version; Leaderboard chỉ projection những result đủ điều kiện và cho phép drill-down về evidence. Đây là ý chính của kiến trúc: các phần có thể thay đổi tương đối độc lập, nhưng kết quả cuối vẫn đúng, có thể giải thích và chạy lại.
