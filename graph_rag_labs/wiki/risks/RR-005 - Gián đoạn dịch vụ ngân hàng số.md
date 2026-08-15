---
id: RR-005
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-005 - Gián đoạn dịch vụ ngân hàng số

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-005`
- **Tên rủi ro**: Gián đoạn dịch vụ ngân hàng số
- **Danh mục (Category)**: Rui ro cong nghe thong tin
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-IT`

## 📝 Mô tả Chi tiết
Hệ thống thanh toán trực tuyến không sẵn sàng

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Kế hoạch năng lực và dự phòng chưa đầy đủ
- **Sự kiện (Event)**: Dịch vụ ngân hàng số bị gián đoạn
- **Tác động / Hậu quả (Impact)**: Mất doanh thu và khiếu nại khách hàng

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-005 - Kiểm thử khả năng chịu tải và chuyển đổi dự phòng]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: kiểm thử dự phòng giảm gián đoạn dịch vụ")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-005 - Dịch vụ ngân hàng số gián đoạn trong giờ cao điểm]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện gián đoạn dịch vụ")*
