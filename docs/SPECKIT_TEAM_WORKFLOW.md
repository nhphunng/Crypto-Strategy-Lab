# Spec + Plan

**Mục tiêu:** mỗi người viết `spec` và `plan` cho một feature. Chưa implement code.

## 1. Phân công

|Người|Feature|Nội dung chính|
|---|---|---|
|TV1|`001-historical-market-data`|Lấy, chuẩn hóa, lưu dữ liệu giá lịch sử|
|TV2|`002-realtime-multi-chart`|Dữ liệu realtime, tối đa 4 biểu đồ|
|TV3|`003-strategy-foundation`|Strategy chung, MA, RSI và đăng ký strategy|
|TV4|`004-backtest-evaluation`|Mô phỏng giao dịch và tính kết quả|
|TV5|`005-leaderboard-visualization`|Bảng xếp hạng và hiển thị điểm mua/bán|

TV1 và TV3 cần chốt định dạng dữ liệu sớm vì TV4 phụ thuộc vào hai feature này.

## 2. Mỗi người cần tạo gì?

```
specs/<feature>/
├── spec.md          # Feature cần làm gì
├── plan.md          # Sẽ xây như thế nào
├── research.md      # Quyết định và lý do
├── data-model.md    # Dữ liệu cần lưu
├── quickstart.md    # Cách kiểm tra feature
├── contracts/       # API hoặc dữ liệu trao đổi
├── checklists/
└── tasks.md         # Danh sách việc cần code
```

- `spec.md`: viết yêu cầu, user story, trường hợp lỗi, kết quả mong đợi. Không ghi công nghệ.
- `plan.md`: ghi công nghệ, cấu trúc code, database, API và cách test.

## 3. Cách dùng Spec Kit

Mỗi người chạy theo đúng thứ tự:

```
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Ý nghĩa:

1. `specify`: tạo yêu cầu cho feature.
2. `clarify`: làm rõ điểm còn mơ hồ.
3. `plan`: thiết kế kỹ thuật và tạo tài liệu liên quan.
4. `checklist`: kiểm tra yêu cầu đã đủ và rõ chưa.
5. `tasks`: chia thành việc implementation cụ thể.
6. `analyze`: tìm mâu thuẫn giữa spec, plan và tasks.

**Dừng sau `analyze`. Chưa chạy `speckit-implement`.**

## 4. Quản lý Git

Trước khi chia branch, merge tài liệu nền vào `main`.

Mỗi người tạo branch riêng:

```
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feat/001-market-data-spec-plan
```

Tên branch còn lại:

```
feat/002-realtime-chart-spec-plan
feat/003-strategy-foundation-spec-plan
feat/004-backtest-evaluation-spec-plan
feat/005-leaderboard-spec-plan
```

Quy tắc:

- Không push trực tiếp vào `main`.
- Không viết code trong PR này.
- Mỗi người dùng máy, clone hoặc Git worktree riêng.
- Không commit `.specify/feature.json` và dữ liệu `.codegraph/`.
- Mỗi PR chỉ chứa tài liệu của một feature.

## 5. Nội dung cần đối chiếu

|Feature liên quan|Phải thống nhất|
|---|---|
|TV1 ↔ TV2|Cấu trúc candle, timeframe, timestamp và dữ liệu thiếu|
|TV1 ↔ TV4|Dataset dùng cho backtest, khoảng ngày và dữ liệu trùng|
|TV3 ↔ TV4|Input strategy, tham số và định dạng BUY/SELL/HOLD|
|TV4 ↔ TV5|Trade, metrics, score và dữ liệu bảng xếp hạng|
|Tất cả|Tên thuật ngữ, ID, error format và version|

Review chéo:

```
TV1 review TV2
TV2 review TV3
TV3 review TV4
TV4 review TV5
TV5 review TV1
```

## Điều kiện hoàn thành

Một feature chỉ được chuyển sang implementation khi:

- `spec.md` rõ phạm vi và kiểm thử được.
- `plan.md` khớp với spec.
- Contract khớp với feature liên quan.
- `tasks.md` không bỏ sót yêu cầu.
- `speckit-analyze` không còn lỗi nghiêm trọng.

**Việc đầu tiên:** cả nhóm họp 60 phút để duyệt tên, phạm vi và quan hệ của 5 feature trước khi tạo branch.