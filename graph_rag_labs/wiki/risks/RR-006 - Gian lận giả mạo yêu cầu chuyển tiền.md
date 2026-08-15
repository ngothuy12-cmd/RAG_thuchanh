---
id: RR-006
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-006 - Gian lận giả mạo yêu cầu chuyển tiền

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-006`
- **Tên rủi ro**: Gian lận giả mạo yêu cầu chuyển tiền
- **Danh mục (Category)**: Rui ro gian lan
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-OPS`

## 📝 Mô tả Chi tiết
Nhận diện và xác thực yêu cầu chưa đủ mạnh

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Nhân viên không xác minh kênh liên lạc
- **Sự kiện (Event)**: Yêu cầu chuyển tiền giả mạo được xử lý
- **Tác động / Hậu quả (Impact)**: Tổn thất tài chính

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-006 - Xác thực hai kênh với lệnh chuyển tiền ngoại lệ]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: xác thực hai kênh giảm gian lận chuyển tiền")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-006 - Yêu cầu chuyển tiền giả mạo được xử lý trước khi bị thu hồi]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện giả mạo chuyển tiền")*
