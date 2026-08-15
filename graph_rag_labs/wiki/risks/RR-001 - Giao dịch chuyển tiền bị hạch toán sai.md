---
id: RR-001
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-001 - Giao dịch chuyển tiền bị hạch toán sai

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-001`
- **Tên rủi ro**: Giao dịch chuyển tiền bị hạch toán sai
- **Danh mục (Category)**: Rui ro van hanh
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-OPS`

## 📝 Mô tả Chi tiết
Đối soát giao dịch cuối ngày không đầy đủ

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Thiếu đối chiếu giữa hệ thống thanh toán và sổ cái
- **Sự kiện (Event)**: Giao dịch được ghi nhận sai trạng thái
- **Tác động / Hậu quả (Impact)**: Tổn thất tài chính và khiếu nại khách hàng

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-001 - Đối soát tự động giao dịch và sổ cái]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: đối soát tự động giảm nguy cơ hạch toán sai")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-001 - Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện đối soát giao dịch")*
