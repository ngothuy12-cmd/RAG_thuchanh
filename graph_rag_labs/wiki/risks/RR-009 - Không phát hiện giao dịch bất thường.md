---
id: RR-009
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-009 - Không phát hiện giao dịch bất thường

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-009`
- **Tên rủi ro**: Không phát hiện giao dịch bất thường
- **Danh mục (Category)**: Rui ro gian lan
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-OPS`

## 📝 Mô tả Chi tiết
Luật phát hiện gian lận không được cập nhật

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Ngưỡng cảnh báo không phù hợp
- **Sự kiện (Event)**: Giao dịch nghi ngờ không bị chặn kịp thời
- **Tác động / Hậu quả (Impact)**: Tổn thất tài chính và uy tín

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-009 - Hiệu chỉnh luật phát hiện giao dịch gian lận]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: hiệu chỉnh luật giảm bỏ sót giao dịch bất thường")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-009 - Giao dịch bất thường chỉ bị phát hiện sau khi khách hàng khiếu nại]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện không phát hiện bất thường")*
