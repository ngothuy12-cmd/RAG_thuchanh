---
id: RR-008
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-008 - Định giá tài sản bảo đảm không chính xác

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-008`
- **Tên rủi ro**: Định giá tài sản bảo đảm không chính xác
- **Danh mục (Category)**: Rui ro tin dung
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-CREDIT`

## 📝 Mô tả Chi tiết
Dữ liệu định giá không độc lập hoặc hết hạn

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Thiếu rà soát lại giá trị tài sản
- **Sự kiện (Event)**: Tài sản bảo đảm được định giá cao hơn thực tế
- **Tác động / Hậu quả (Impact)**: Tăng tổn thất khi xử lý nợ

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-008 - Rà soát độc lập định giá tài sản bảo đảm]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: rà soát độc lập giảm sai định giá")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-008 - Rà soát phát hiện giá trị tài sản bảo đảm đã hết hiệu lực]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện sai định giá tài sản")*
