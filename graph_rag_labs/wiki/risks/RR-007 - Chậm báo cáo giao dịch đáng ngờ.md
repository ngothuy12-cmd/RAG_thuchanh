---
id: RR-007
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-007 - Chậm báo cáo giao dịch đáng ngờ

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-007`
- **Tên rủi ro**: Chậm báo cáo giao dịch đáng ngờ
- **Danh mục (Category)**: Rui ro tuan thu
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-COMPLIANCE`

## 📝 Mô tả Chi tiết
Theo dõi cảnh báo AML không kịp thời

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Khối lượng cảnh báo vượt năng lực xử lý
- **Sự kiện (Event)**: Báo cáo giao dịch đáng ngờ nộp muộn
- **Tác động / Hậu quả (Impact)**: Chế tài và rủi ro pháp lý

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-007 - Theo dõi SLA xử lý cảnh báo AML]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: theo dõi SLA giảm nguy cơ báo cáo muộn")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-007 - Báo cáo giao dịch đáng ngờ nộp quá hạn nội bộ]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện báo cáo AML muộn")*
