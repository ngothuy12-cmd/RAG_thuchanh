---
id: RR-010
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RR-010 - Sai lệch số liệu báo cáo quản trị

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `RR-010`
- **Tên rủi ro**: Sai lệch số liệu báo cáo quản trị
- **Danh mục (Category)**: Rui ro bao cao
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Trung binh`
- **Mức độ rủi ro còn lại (Residual Level)**: `Thap`
- **Đơn vị phụ trách (Owner Unit ID)**: `DV-FINANCE`

## 📝 Mô tả Chi tiết
Dữ liệu nguồn không được đối chiếu

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: Thay đổi dữ liệu không có kiểm soát
- **Sự kiện (Event)**: Báo cáo quản trị có số liệu sai
- **Tác động / Hậu quả (Impact)**: Quyết định quản trị sai lệch

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
- [[KS-010 - Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]] *(Quan hệ: `MITIGATES` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: đối chiếu nguồn giảm sai lệch báo cáo")*

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
- [[SK-010 - Báo cáo quản trị sử dụng dữ liệu nguồn chưa đối chiếu]] *(Quan hệ: `OBSERVED_AS` | Trạng thái: `VERIFIED` | Bằng chứng: "Dữ liệu mô phỏng: sự kiện sai lệch báo cáo")*
