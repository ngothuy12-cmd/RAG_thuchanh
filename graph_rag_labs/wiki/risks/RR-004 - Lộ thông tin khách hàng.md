---
id: RR-004
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-004 - Lộ thông tin khách hàng

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-004`
- **Tên rủi ro**: Lộ thông tin khách hàng
- **Danh mục (Category)**: Rui ro cong nghe thong tin
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-IT`

## 📝 Mô tả Chi tiết
Quyền truy cập dữ liệu không được kiểm soát phù hợp

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Cấp quyền vượt nhu cầu công việc
- **Sự kiện (Event)**: Dữ liệu khách hàng bị truy cập hoặc chia sẻ trái phép
- **Tác động / Hậu quả (Impact)**: Vi phạm bảo mật và tổn hại uy tín

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-004 - Rà soát quyền truy cập định kỳ]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: rà soát quyền hạn giảm lộ dữ liệu")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-004 - Tài khoản có quyền truy cập dữ liệu vượt phạm vi công việc]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện quyền truy cập quá mức")*
