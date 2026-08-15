---
id: RR-002
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-002 - Phê duyệt tín dụng vượt thẩm quyền

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-002`
- **Tên rủi ro**: Phê duyệt tín dụng vượt thẩm quyền
- **Danh mục (Category)**: Rui ro tin dung
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-CREDIT`

## 📝 Mô tả Chi tiết
Kiểm tra hạn mức phê duyệt không hiệu lực

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Phân quyền trên hệ thống không cập nhật
- **Sự kiện (Event)**: Khoản vay được phê duyệt vượt thẩm quyền
- **Tác động / Hậu quả (Impact)**: Tăng nợ xấu và vi phạm quy định

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-002 - Kiểm tra hạn mức phê duyệt trên hệ thống]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: kiểm tra hạn mức ngăn phê duyệt vượt thẩm quyền")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-002 - Hồ sơ tín dụng được phê duyệt vượt hạn mức của người phê duyệt]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện vượt thẩm quyền")*
