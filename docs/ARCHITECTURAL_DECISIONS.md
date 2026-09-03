# Crypto Strategy Lab

## Báo cáo các quyết định kiến trúc

**Ngày cập nhật:** 03/09/2026

## 1. Cơ sở lựa chọn kiến trúc

Crypto Strategy Lab cần hỗ trợ một quy trình liên tục: nhận dữ liệu thị trường, phân tích chiến lược, tạo tổ hợp, backtest, đánh giá và cập nhật bảng xếp hạng. Điểm khó không nằm ở một chỉ báo cụ thể, mà ở việc duy trì quy trình đó khi chiến lược, nguồn dữ liệu hoặc cách tìm kiếm thay đổi.

Vì vậy, các lựa chọn kiến trúc tập trung vào bốn mục tiêu: phân chia trách nhiệm rõ ràng, giảm phụ thuộc giữa các thành phần, giữ khả năng giải thích kết quả và tạo đường mở rộng phù hợp với khối lượng xử lý. Công nghệ chỉ được lựa chọn khi phục vụ những mục tiêu này.

Báo cáo trình bày lý do, phương án thay thế và hệ quả của từng lựa chọn. Các mã D-01 đến D-11 được dùng để tiện tham chiếu trong báo cáo. Chúng không thay thế các ADR đã lưu trong repository. Riêng D-11 mô tả hướng phát triển cho xử lý phân tán, chưa phải cấu hình đang triển khai.

| Mã | Nội dung quyết định | Mục tiêu chính |
| --- | --- | --- |
| D-01 | Tổ chức backend theo modular monolith | Giữ triển khai gọn và phân chia mô-đun rõ ràng |
| D-02 | Phân lớp và sử dụng các giao diện tại ranh giới hệ thống | Giảm ảnh hưởng khi thay đổi thành phần |
| D-03 | Kết hợp REST và WebSocket | Cung cấp dữ liệu có thể tải lại và cập nhật thời gian thực |
| D-04 | Chuẩn hóa dữ liệu thị trường | Độc lập với nhà cung cấp và nhất quán dữ liệu |
| D-05 | Quản lý chiến lược qua registry và phiên bản | Bổ sung chiến lược mà ít ảnh hưởng quy trình chung |
| D-06 | Tách sinh ứng viên khỏi quy trình thử nghiệm | Thay thuật toán tìm kiếm và kiểm soát chi phí chạy |
| D-07 | Tách backtest, đánh giá và xếp hạng | Bảo đảm trách nhiệm rõ và kết quả có thể giải thích |
| D-08 | Lưu dữ liệu và trạng thái xếp hạng trong PostgreSQL | Giữ lịch sử và hỗ trợ truy vết |
| D-09 | Tách thu thập tin khỏi phân tích sentiment | Thay bộ phân tích và giới hạn ảnh hưởng của lỗi |
| D-10 | Cô lập mã chiến lược được sinh tự động | Bảo vệ ứng dụng và dữ liệu |
| D-11 | Mở rộng bằng hàng đợi và worker độc lập | Tăng năng lực xử lý và phục hồi công việc |

## 2. D-01 — Tổ chức backend theo modular monolith

### Bài toán đặt ra

Hệ thống có nhiều nghiệp vụ nhưng vẫn cần chạy được trong một môi trường phát triển và trình diễn đơn giản. Nếu mỗi nghiệp vụ trở thành một dịch vụ riêng ngay từ đầu, việc quản lý triển khai, kết nối mạng và lỗi giữa các dịch vụ sẽ chiếm nhiều công sức của nhóm.

### Lựa chọn và lý do

Backend được tổ chức thành các mô-đun trong cùng một ứng dụng. Giao diện, API và PostgreSQL chạy ở các container riêng; một công việc migration chuẩn bị lược đồ trước khi API khởi động. Mỗi mô-đun giữ trách nhiệm riêng, trong khi toàn bộ hệ thống vẫn có thể được khởi động bằng Docker Compose.

So với microservices, lựa chọn này giảm số đơn vị cần triển khai và giúp kiểm thử các luồng nghiệp vụ thuận tiện hơn. So với một ứng dụng không phân chia mô-đun, nó vẫn tạo ra vị trí rõ ràng cho chiến lược, dữ liệu thị trường, backtest và đánh giá.

### Hệ quả

Đổi lại sự đơn giản, các tác vụ nền hiện chia sẻ tiến trình API và cơ sở dữ liệu. Một tác vụ sử dụng nhiều CPU hoặc lỗi ở thành phần dùng chung có thể ảnh hưởng đến phần còn lại. Tác vụ bất đồng bộ hỗ trợ tổ chức công việc nhưng không thay thế worker xử lý độc lập.

[ADR-001](ADR/ADR-001-modular-monolith-and-workers.md) xác định hướng tách worker thành tiến trình riêng. Hướng này chưa có trong Compose mặc định và được phát triển tiếp ở D-11. Quyết định tách sẽ dựa trên nhu cầu phục hồi công việc và kết quả đo tải.

## 3. D-02 — Phân lớp và đặt giao diện tại các ranh giới dễ thay đổi

Một nguồn dữ liệu mới không nên buộc sửa công thức RSI; thay cơ sở dữ liệu cũng không nên làm thay đổi cách tính lợi nhuận. Để giữ những thay đổi này độc lập, mã nguồn được chia thành Domain, Application, Infrastructure và API.

Domain mô tả dữ liệu và quy tắc nghiệp vụ. Application điều phối các ca sử dụng. Infrastructure cung cấp cách truy cập cơ sở dữ liệu hoặc dịch vụ ngoài. API đảm nhiệm giao tiếp và kết nối các thành phần khi ứng dụng khởi động. Các giao diện như nguồn dữ liệu thị trường, kho lưu trữ và bộ phân tích sentiment được đặt tại những nơi có nhu cầu thay thế thực tế.

Phương án để controller gọi trực tiếp mọi dịch vụ và bảng dữ liệu có thể làm mã ban đầu ngắn hơn, nhưng dễ khiến các quy tắc nghiệp vụ bị phân tán. Ở chiều ngược lại, tạo một lớp trừu tượng cho mọi hàm nhỏ cũng làm hệ thống khó đọc. Vì vậy, việc phân lớp tập trung vào những ranh giới có ý nghĩa về nghiệp vụ hoặc khả năng thay đổi.

Cách tổ chức này hỗ trợ kiểm thử nghiệp vụ bằng dữ liệu giả lập mà không cần kết nối mạng. Chi phí là có thêm các kiểu dữ liệu, bộ chuyển đổi và giao diện phải được duy trì nhất quán. Hiện dịch vụ tìm kiếm còn phụ thuộc kiểu cụ thể của Random Search; giao diện đọc sentiment cũng cần được bố trí lại để phù hợp hoàn toàn với hướng phân lớp.

Quyết định kế thừa [ADR-002](ADR/ADR-002-layered-boundaries.md). Các kiểm thử ranh giới phụ thuộc và kiểm thử thay bộ kết nối là cơ sở đánh giá lựa chọn này.

## 4. D-03 — REST cho lịch sử và trạng thái, WebSocket cho thời gian thực

### Vì sao không chỉ dùng polling?

Biểu đồ cần cập nhật liên tục, trong khi người dùng có thể mở đồng thời bốn khung thời gian. Nếu mỗi biểu đồ gửi yêu cầu lấy giá lặp lại, số lượng request tăng theo số biểu đồ và số người dùng; độ trễ cũng phụ thuộc vào chu kỳ polling.

Hệ thống sử dụng REST để tải lịch sử, trạng thái hiện tại và thông tin chi tiết. WebSocket truyền các cập nhật thời gian thực và hỗ trợ quản lý đăng ký theo cặp giao dịch, khung thời gian. Backend có thể dùng chung một kết nối nguồn cho nhiều đăng ký tương đương.

SSE là phương án phù hợp cho luồng một chiều từ server, nhưng việc thay đổi đăng ký cần được tổ chức qua một kênh yêu cầu riêng. Để trình duyệt gọi thẳng Binance lại khiến giao diện phụ thuộc định dạng của sàn và phân tán logic phục hồi kết nối. Kết hợp REST và WebSocket giữ các trách nhiệm này ở backend.

### Những trách nhiệm đi kèm

WebSocket không tự giải quyết mất kết nối, bản tin trùng hoặc dữ liệu đến sai thứ tự. Hệ thống phải quản lý vòng đời đăng ký, trạng thái dữ liệu cũ, kết nối lại và bù khoảng dữ liệu thiếu. REST vẫn cần thiết để tải lại một trạng thái đầy đủ thay vì phụ thuộc hoàn toàn vào các bản tin đã nhận.

Các tình huống kiểm chứng gồm đổi một khung thời gian mà không ảnh hưởng các biểu đồ khác, chia sẻ luồng dữ liệu giữa nhiều người dùng và phục hồi sau khi ngắt kết nối. Khi triển khai nhiều tiến trình API, kênh phân phối cập nhật cần được mở rộng để không phụ thuộc vào bộ nhớ của một tiến trình.

## 5. D-04 — Chuẩn hóa dữ liệu thị trường trước khi đưa vào nghiệp vụ

Binance cung cấp dữ liệu theo quy ước riêng. Nếu các thành phần sử dụng trực tiếp cấu trúc đó, việc thêm một sàn mới sẽ làm thay đổi cả giao diện, chiến lược và backtest. Hệ thống vì vậy chuyển dữ liệu nhà cung cấp thành cấu trúc Candle chung.

Mỗi nến được nhận dạng bằng nguồn dữ liệu, cặp giao dịch, khung thời gian và thời điểm mở. Thời gian được thống nhất về UTC; các giá trị OHLCV được kiểm tra trước khi lưu. Tập dữ liệu backtest còn lưu khoảng thời gian, mức độ đầy đủ, phiên bản cấu trúc và mã kiểm tra nội dung.

Chỉ lưu giá đóng cửa là phương án đơn giản hơn nhưng không đủ cho biểu đồ nến và nhiều chiến lược. Lấy dữ liệu trực tiếp từ nhà cung cấp mỗi lần chạy lại cũng khiến việc so sánh hai lần thử nghiệm khó kiểm soát hơn.

Lợi ích của chuẩn hóa là các thành phần nghiệp vụ nhận một cấu trúc ổn định. Chi phí nằm ở việc ánh xạ dữ liệu, xử lý độ chính xác và mô tả những khả năng khác nhau của từng nguồn. Khi thêm nhà cung cấp, phần lựa chọn nguồn trên giao diện có thể cần bổ sung, nhưng bộ vẽ biểu đồ không phải hiểu dữ liệu gốc của sàn mới.

[ADR-003](ADR/ADR-003-normalized-market-data.md) quy định chi tiết lựa chọn này. Việc kiểm chứng gồm nhập lại cùng khoảng dữ liệu không tạo nến trùng, phát hiện khoảng thiếu và xác nhận các nguồn tuân theo cùng giao diện.

## 6. D-05 — Registry và phiên bản cho chiến lược

### Quản lý chiến lược như thành phần có thể bổ sung

Hệ thống cần thêm một chiến lược như MACD mà không sửa nhiều nhánh điều kiện ở Backtester hoặc bảng xếp hạng. Mỗi chiến lược vì vậy cung cấp cách phân tích, mô tả tham số và thông tin phiên bản; registry tập hợp các chiến lược khả dụng.

Giao diện đọc danh mục và tham số từ backend. Cấu hình đã lưu tham chiếu đến định nghĩa và phiên bản cụ thể. Chiến lược tổng hợp lưu các thành viên cùng quy tắc bỏ phiếu hoặc trọng số, rồi tạo đầu ra chung để các bước sau sử dụng.

### Phương án khác và sự đánh đổi

Viết riêng một nhánh cho mỗi tổ hợp có thể thuận tiện khi chỉ có hai hoặc ba trường hợp, nhưng số nhánh tăng nhanh khi bổ sung chiến lược. Tính toán trong trình duyệt tạo nguy cơ lệch logic giữa giao diện và backend. Cho phép chiến lược tự truy cập cơ sở dữ liệu lại làm đầu vào khó kiểm soát.

Registry và giao diện chung giảm những phụ thuộc này, nhưng yêu cầu quản lý phiên bản rõ ràng. Thay bộ tham số tạo định nghĩa hoặc cấu hình mới; thay hành vi thuật toán cần phiên bản chiến lược mới. Kết quả cũ tiếp tục tham chiếu đúng cấu hình đã dùng.

Các quy tắc kết hợp cũng cần xử lý tín hiệu cùng thời điểm, trường hợp bằng phiếu và giai đoạn chưa đủ dữ liệu. Đây là phần nghiệp vụ riêng của chiến lược tổng hợp, không phải trách nhiệm của Backtester.

Lựa chọn được mô tả trong [ADR-004](ADR/ADR-004-strategy-plugin-and-versioning.md). Một phép kiểm chứng quan trọng là bổ sung chiến lược mới bằng cách viết lớp xử lý, khai báo thông tin, đăng ký vào danh mục và thêm kiểm thử mà không sửa logic mô phỏng hay chấm điểm.

## 7. D-06 — Tách bộ sinh ứng viên khỏi quy trình tìm kiếm

Không gian tổ hợp và tham số có thể tăng rất nhanh. Duyệt toàn bộ dễ giải thích nhưng tốn nhiều lần chạy; các thuật toán như genetic search hoặc Bayesian optimization lại cần thêm cấu trúc và ngân sách thử nghiệm. Random Search được dùng làm phương pháp ban đầu vì đáp ứng yêu cầu cốt lõi và có quy trình tương đối đơn giản.

Bộ sinh ứng viên chỉ chọn các chiến lược, phiên bản và tham số để tạo `StrategyCandidate`. Dịch vụ tìm kiếm chịu trách nhiệm lưu lần chạy, gọi phân tích, backtest, đánh giá và cập nhật tiến độ. Nó không chứa lại công thức của từng bước.

Seed giúp kiểm soát phần ngẫu nhiên khi tập đầu vào và danh mục chiến lược được giữ nguyên. Dấu vân tay cấu hình giúp tránh sinh lại cùng một ứng viên trong một lần tìm kiếm. Các giới hạn về số ứng viên, thời gian, số lần không cải thiện và yêu cầu hủy giúp kiểm soát công việc.

Đổi lại, phiên bản hiện tại xử lý ứng viên tuần tự trong tác vụ của API. Thời gian được kiểm tra giữa các ứng viên và tiến độ WebSocket được phân phối trong tiến trình. Lịch sử đã lưu không tự khởi động lại công việc bị gián đoạn. Ngoài ra, dịch vụ vẫn khai báo kiểu `RandomSearchGenerator`; khi tích hợp thuật toán mới cần chuyển phụ thuộc này sang giao diện chung và chỉnh phần khởi tạo.

Việc thay thuật toán không làm thay đổi cấu trúc đầu ra của ứng viên, nên quy trình Backtest, Evaluation và Leaderboard có thể được giữ nguyên. Kiểm thử cần tập trung vào tính nhất quán của seed, tính hợp lệ của tham số, loại trùng và các điều kiện dừng.

## 8. D-07 — Tách backtest, đánh giá và xếp hạng

Một chiến lược có tỷ suất sinh lời cao vẫn có thể đi kèm sụt giảm tài sản lớn. Vì vậy, hệ thống không dùng lợi nhuận như tiêu chí duy nhất, cũng không gộp toàn bộ xử lý vào một dịch vụ.

Backtester mô phỏng giao dịch và biến động tài sản. Bộ đánh giá tính Return, Win Rate, Max Drawdown, Number of Trades và các chỉ số bổ sung. Chính sách chấm điểm quy định cách chuẩn hóa, trọng số và xử lý chỉ số không xác định. Bảng xếp hạng sử dụng kết quả đã lưu để chọn Top-K và giải quyết các trường hợp bằng điểm.

Chính sách Balanced v1 hiện phân bổ trọng số 35% cho Return, 25% cho Win Rate, 25% cho Max Drawdown và 15% cho Sharpe. Các giá trị được giới hạn và chuẩn hóa trước khi tính tổng có trọng số. Đây là một lựa chọn của hệ thống, không phải công thức bắt buộc của đề bài.

Chấm điểm trực tiếp trên giao diện sẽ tạo thêm một nơi chứa quy tắc nghiệp vụ. Cộng các chỉ số thô khác đơn vị khiến điểm tổng khó giải thích. Việc phân chia trách nhiệm và quản lý chính sách theo phiên bản cho phép thay cách đánh giá mà không cần sửa chiến lược hoặc ghi đè kết quả cũ.

Chi phí của lựa chọn này là phải lưu nhiều thông tin hơn và kiểm tra sự nhất quán giữa giao dịch, biến động tài sản, chỉ số và điểm số. Các trường hợp không có giao dịch hoặc chỉ số không xác định cần quy tắc rõ ràng. Kiểm thử chạy lại cùng đầu vào và đối chiếu các số liệu là cơ sở đánh giá tính đúng đắn.

Lựa chọn này gắn với [ADR-005](ADR/ADR-005-reproducible-backtesting.md).

## 9. D-08 — PostgreSQL và trạng thái bảng xếp hạng được lưu lâu dài

Các cấu hình, lần chạy và kết quả cần tồn tại sau khi người dùng tải lại trang. Chúng cũng có nhiều quan hệ: một ứng viên thuộc một lần tìm kiếm, tạo ra một backtest, rồi được đánh giá và đưa vào bảng xếp hạng. PostgreSQL được dùng để lưu những dữ liệu này với các ràng buộc và giao dịch nhất quán.

Các mô-đun truy cập dữ liệu thông qua kho lưu trữ chuyên trách. Alembic quản lý thay đổi lược đồ. Bảng xếp hạng lưu trạng thái Top-K, phiên bản và các bản ghi cập nhật để hỗ trợ thông báo thay đổi; REST cung cấp trạng thái đầy đủ khi giao diện cần tải lại.

Lưu toàn bộ trong bộ nhớ hoặc trình duyệt sẽ đơn giản hơn nhưng không phù hợp với lịch sử thử nghiệm có thể truy vết. Tách cơ sở dữ liệu theo từng mô-đun hoặc áp dụng event sourcing toàn bộ lại làm triển khai và truy vấn liên mô-đun phức tạp hơn so với nhu cầu hiện tại.

Sử dụng một cơ sở dữ liệu chung giúp triển khai gọn nhưng cũng tạo điểm nghẽn và phạm vi ảnh hưởng chung khi có lỗi. Chỉ mục, truy vấn và quyền sở hữu dữ liệu giữa các mô-đun cần được duy trì rõ ràng.

Một điểm cần phân biệt là các bản ghi cập nhật bảng xếp hạng được lưu bền vững, còn kênh tiến độ tìm kiếm hiện nằm trong bộ nhớ. Hệ thống kết hợp lời gọi trực tiếp giữa các dịch vụ và thông báo sự kiện, chưa sử dụng một hệ thống sự kiện phân tán cho toàn bộ quy trình.

Kiểm chứng tập trung vào khả năng đọc lại sau khi khởi động lại, cập nhật không tạo kết quả trùng và migration trên cơ sở dữ liệu kiểm thử riêng.

## 10. D-09 — Tách thu thập tin tức khỏi phân tích sentiment

### Hai công việc có vòng đời khác nhau

Thu thập tin phụ thuộc vào nguồn RSS/Atom, trong khi phân tích phụ thuộc vào thuật toán hoặc mô hình. Nếu gọi bộ phân tích ngay trong quá trình thu thập, một mô hình chậm hoặc lỗi có thể làm gián đoạn cả việc lưu tin.

Hệ thống tách hai bước: `CollectNews` lưu tin đã chuẩn hóa; `AnalyzePendingNews` đọc những tin cần xử lý và gọi bộ phân tích qua `SentimentAnalyzer`. Mỗi kết quả phân tích nằm trong bản ghi riêng, có phiên bản và liên kết đến nội dung tin.

### Lợi ích và giới hạn

Thay bộ phân tích không đòi hỏi sửa bộ thu thập. Kết quả cũ vẫn có thể được nhận dạng theo phiên bản đã tạo ra nó. Ghi đè một cột sentiment trên bản ghi tin sẽ ít bảng hơn, nhưng làm mất lịch sử khi nội dung hoặc thuật toán thay đổi.

`NewsSentimentStrategy` đọc dữ liệu qua giao diện chung và chỉ sử dụng tin đã xuất bản, đã phân tích trước thời điểm ra quyết định. Khi thiếu dữ liệu, chiến lược giữ trạng thái HOLD/WARMUP. Để bảo đảm thử nghiệm có thể chạy lại đầy đủ, tập tin và phiên bản phân tích đã sử dụng cần được cố định cùng lần chạy.

Bộ phân tích hiện tại sử dụng từ điển từ khóa. Ưu điểm là nhẹ, dễ giải thích và cho kết quả nhất quán. Tuy nhiên, đây là phương pháp dựa trên quy tắc, chưa đáp ứng yêu cầu mô hình học máy của đồ án. Bước hoàn thiện tiếp theo là đưa một mô hình đã huấn luyện vào sau giao diện hiện có, quản lý phiên bản và đánh giá trên tập tin có nhãn. Chi phí tài nguyên, quyền sử dụng dữ liệu và khả năng xử lý lỗi cũng cần được xem xét khi chọn mô hình.

[ADR-007](ADR/ADR-007-news-provider-pipeline.md) mô tả ranh giới thu thập và phân tích. Việc kiểm chứng bao gồm lỗi từng tin, thay phiên bản bộ phân tích, không sử dụng dữ liệu tương lai và chất lượng phân loại khi có mô hình học máy.

## 11. D-10 — Cô lập mã chiến lược được sinh tự động

Phần mở rộng LLM tạo ra một rủi ro khác với các chiến lược do người phát triển viết sẵn: mã được sinh tự động và nội dung nguồn chưa thể được coi là đáng tin cậy. Thực thi trực tiếp trong API có thể làm lộ dữ liệu hoặc ảnh hưởng đến tiến trình ứng dụng.

Vì vậy, kết quả được lưu dưới dạng bản nháp, trải qua kiểm tra tĩnh và kiểm tra trong môi trường cô lập. Chỉ sau khi có kết quả kiểm tra phù hợp và được người dùng xác nhận, phiên bản cụ thể mới được kích hoạt. Nội dung, kết quả kiểm tra và thông tin nguồn được liên kết bằng định danh và mã kiểm tra.

Chỉ kiểm tra cú pháp hoặc lint chưa đủ để kiểm soát hành vi khi chạy. Cấm hoàn toàn việc sinh mã sẽ giảm rủi ro nhưng loại bỏ chức năng mở rộng. Môi trường cô lập là phương án dung hòa, với điều kiện giới hạn quyền, tài nguyên và khả năng truy cập của mã.

Lựa chọn này làm tăng chi phí triển khai và quản lý các tệp mã chiến lược. Nó yêu cầu cấu hình riêng, không được kích hoạt khi thiếu điều kiện an toàn và không thay thế hệ thống phân quyền nhiều người dùng. Các quy tắc chi tiết nằm trong [ADR-006](ADR/ADR-006-llm-generated-strategy-isolation.md) và [chính sách an toàn](GENERATED_STRATEGY_SECURITY_POLICY.md).

Việc kiểm chứng cần bao gồm đường đi từ bản nháp đến kích hoạt, kiểm tra đúng mã được chạy và xác nhận mã không tiếp cận thông tin bí mật của ứng dụng.

## 12. D-11 — Hướng mở rộng bằng hàng đợi và worker độc lập

### Khi nào cần thay đổi?

Khi số lượng backtest tăng lên hàng chục hoặc hàng trăm nghìn, việc chạy trong tiến trình API không còn phù hợp. Tăng số tác vụ bất đồng bộ không tự tăng năng lực tính toán; tăng số API replica cũng có thể làm các vòng lặp nền chạy trùng và khiến kênh tiến độ bị chia cắt.

Hướng phát triển là tách tiếp nhận yêu cầu khỏi thực thi công việc. API hoặc dịch vụ tìm kiếm tạo các công việc được lưu bền vững. Hàng đợi phân phối công việc đến worker độc lập; worker sử dụng lại các thành phần Backtest và Evaluation để ghi kết quả.

### Các lựa chọn và hệ quả

Một nhóm tiến trình xử lý cục bộ có thể tăng năng lực tính toán, nhưng vẫn cần cơ chế lưu và nhận lại công việc khi lỗi. Một broker hỗ trợ phân phối giữa nhiều máy, đổi lại phải vận hành thêm thành phần và xử lý tình huống một công việc được giao nhiều lần. Tách toàn bộ hệ thống thành microservices không phải điều kiện bắt buộc để thêm worker.

Thiết kế cần có định danh công việc, thời hạn giữ việc, tín hiệu sống từ worker, giới hạn thử lại, hủy và nơi lưu các công việc thất bại kéo dài. Khi một công việc được nhận lại, các ràng buộc và quy tắc ghi kết quả phải tránh tạo bản sao. Đây là cơ chế xử lý lặp an toàn, thay vì giả định mỗi công việc luôn chỉ được giao đúng một lần.

Công nghệ hàng đợi chưa được chọn trong phiên bản hiện tại. Quyết định sẽ dựa trên nhu cầu vận hành, mức tải và khả năng phục hồi, đồng thời tiếp tục hướng worker tách tiến trình của ADR-001.

### Cách đánh giá

Trước khi chuyển sang mô hình này, cần chạy cùng một tập ứng viên với một và nhiều worker, đối chiếu kết quả và đo năng suất xử lý. Thử dừng rồi khởi động lại worker để kiểm tra nhận lại công việc, xác nhận không tạo kết quả trùng và theo dõi độ trễ API trong lúc chạy tải. Kênh tiến độ cũng phải hoạt động khi người dùng và worker kết nối qua các tiến trình khác nhau.

## 13. Kiểm chứng các lựa chọn kiến trúc

Các quyết định được đánh giá bằng những tình huống thay đổi và lỗi cụ thể, không chỉ bằng sơ đồ hoặc số lượng lớp trong mã nguồn.

| Nội dung cần chứng minh | Tình huống kiểm chứng |
| --- | --- |
| Bổ sung chiến lược ít ảnh hưởng thành phần khác | Thêm một strategy và chạy qua cùng Backtest, Evaluation, Leaderboard |
| Thay thuật toán tìm kiếm | Dùng bộ sinh ứng viên khác nhưng giữ cấu trúc đầu ra và quy trình thử nghiệm |
| Độc lập với nhà cung cấp dữ liệu | Dùng bộ kết nối khác đáp ứng cấu trúc Candle chung |
| Phục hồi dữ liệu thời gian thực | Ngắt kết nối, kết nối lại, bù khoảng thiếu và kiểm tra nến trùng |
| Giải thích và tái tạo kết quả | Đọc đúng cấu hình/phiên bản, chạy lại đầu vào xác định và đối chiếu số liệu |
| Tách tin tức khỏi các chức năng kỹ thuật | Gây lỗi nguồn tin hoặc bộ phân tích và quan sát các luồng còn lại |
| Lưu dữ liệu lâu dài | Tải lại ứng dụng, khởi động lại và đọc lại kết quả đã lưu |
| Mở rộng worker | Đo tải và kiểm tra phục hồi, chống trùng trong kiến trúc mở rộng |

Repository có các bộ kiểm thử cho [ranh giới kiến trúc](../backend/tests/architecture), [khả năng bổ sung chiến lược](../backend/tests/contract/test_strategy_extensibility.py), [Random Search](../backend/tests/unit/strategy/test_random_search_generator.py), [luồng tìm kiếm](../backend/tests/integration/test_strategy_search_flow.py), [phục hồi thời gian thực](../backend/tests/integration/test_realtime_recovery.py) và [sentiment](../backend/tests/unit/sentiment). Kết quả thực nghiệm cần được ghi nhận cùng môi trường và phiên bản mã nguồn tương ứng; sự hiện diện của kiểm thử không tự thay thế bằng chứng chạy thành công.

## 14. Kết luận

Các lựa chọn của Crypto Strategy Lab hướng đến một hệ thống thử nghiệm có thể phát triển dần: dữ liệu được chuẩn hóa, chiến lược được quản lý qua giao diện và phiên bản, còn mô phỏng, đánh giá và trình bày được tách biệt.

Mô hình modular monolith giúp phiên bản hiện tại giữ được quy trình triển khai gọn. Các ranh giới đã hình thành tạo cơ sở để bổ sung nguồn dữ liệu, thuật toán tìm kiếm và bộ phân tích mới. Hai nội dung quan trọng tiếp theo là hoàn thiện mô hình học máy cho sentiment và cơ chế xử lý công việc bền vững khi tăng quy mô. Những phần này được xem là công việc phát triển tiếp, không phải năng lực đã có của cấu hình triển khai hiện tại.

Chi tiết cấu trúc, luồng xử lý và phạm vi triển khai được trình bày trong [Báo cáo kiến trúc phần mềm](ARCHITECTURE.md). Lịch sử các quyết định riêng lẻ được lưu tại [danh mục ADR](ADR/README.md).
