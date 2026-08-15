---
id: HOME
type: Dashboard
verification_status: VERIFIED
data_origin: SYSTEM
---

# 🏠 Wiki Risk Graph - Trang Chủ Tra Cứu Rủi Ro

Chào mừng bạn đến với **Wiki Risk Graph**, hệ thống tri thức rủi ro dạng đồ thị liên kết.

---

## 📊 Thống Kê Tổng Quan Đồ Thị
- **Tổng số Nodes (Thực thể)**: `34`
  - 📋 **Hồ sơ Rủi ro (`RuiRo`)**: `12` nodes
  - 🛡️ **Kiểm soát (`KiemSoat`)**: `10` nodes
  - 💥 **Sự kiện Rủi ro (`SuKienRuiRo`)**: `12` nodes
- **Tổng số Edges (Quan hệ)**: `22`
  - 🛡️ ➡️ 📋 **Giảm thiểu (`MITIGATES`)**: `10` edges
  - 📋 ➡️ 💥 **Biểu hiện (`OBSERVED_AS`)**: `12` edges

---

## 🔗 Danh Mục Liên Kết Nhanh

### 📋 Danh Sách Hồ Sơ Rủi Ro (`risks/`)
- [[RR-001 - Giao dịch chuyển tiền bị hạch toán sai]] - *Rui ro van hanh* (`Cao`)
- [[RR-002 - Phê duyệt tín dụng vượt thẩm quyền]] - *Rui ro tin dung* (`Cao`)
- [[RR-003 - Giải ngân thiếu hồ sơ bảo đảm]] - *Rui ro tin dung* (`Cao`)
- [[RR-004 - Lộ thông tin khách hàng]] - *Rui ro cong nghe thong tin* (`Cao`)
- [[RR-005 - Gián đoạn dịch vụ ngân hàng số]] - *Rui ro cong nghe thong tin* (`Cao`)
- [[RR-006 - Gian lận giả mạo yêu cầu chuyển tiền]] - *Rui ro gian lan* (`Cao`)
- [[RR-007 - Chậm báo cáo giao dịch đáng ngờ]] - *Rui ro tuan thu* (`Cao`)
- [[RR-008 - Định giá tài sản bảo đảm không chính xác]] - *Rui ro tin dung* (`Cao`)
- [[RR-009 - Không phát hiện giao dịch bất thường]] - *Rui ro gian lan* (`Cao`)
- [[RR-010 - Sai lệch số liệu báo cáo quản trị]] - *Rui ro bao cao* (`Trung binh`)
- [[RR-011 - Nhà cung cấp công nghệ không đáp ứng cam kết]] - *Rui ro ben thu ba* (`Trung binh`)
- [[RR-012 - Xung đột lợi ích trong mua sắm]] - *Rui ro dao duc* (`Trung binh`)

---

### 🛡️ Danh Sách Biện Pháp Kiểm Soát (`controls/`)
- [[KS-001 - Đối soát tự động giao dịch và sổ cái]] - *Detective* (`Hieu qua`)
- [[KS-002 - Kiểm tra hạn mức phê duyệt trên hệ thống]] - *Preventive* (`Hieu qua`)
- [[KS-003 - Checklist điều kiện giải ngân bắt buộc]] - *Preventive* (`Can cai thien`)
- [[KS-004 - Rà soát quyền truy cập định kỳ]] - *Preventive* (`Hieu qua`)
- [[KS-005 - Kiểm thử khả năng chịu tải và chuyển đổi dự phòng]] - *Preventive* (`Can cai thien`)
- [[KS-006 - Xác thực hai kênh với lệnh chuyển tiền ngoại lệ]] - *Preventive* (`Hieu qua`)
- [[KS-007 - Theo dõi SLA xử lý cảnh báo AML]] - *Detective* (`Can cai thien`)
- [[KS-008 - Rà soát độc lập định giá tài sản bảo đảm]] - *Detective* (`Hieu qua`)
- [[KS-009 - Hiệu chỉnh luật phát hiện giao dịch gian lận]] - *Preventive* (`Can cai thien`)
- [[KS-010 - Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]] - *Detective* (`Hieu qua`)

---

### 💥 Danh Sách Sự Kiện Rủi Ro (`events/`)
- [[SK-001 - Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày]] - *Mức độ `Trung binh`*
- [[SK-002 - Hồ sơ tín dụng được phê duyệt vượt hạn mức của người phê duyệt]] - *Mức độ `Cao`*
- [[SK-003 - Giải ngân trước khi hoàn thiện chứng từ bảo đảm]] - *Mức độ `Cao`*
- [[SK-004 - Tài khoản có quyền truy cập dữ liệu vượt phạm vi công việc]] - *Mức độ `Cao`*
- [[SK-005 - Dịch vụ ngân hàng số gián đoạn trong giờ cao điểm]] - *Mức độ `Cao`*
- [[SK-006 - Yêu cầu chuyển tiền giả mạo được xử lý trước khi bị thu hồi]] - *Mức độ `Cao`*
- [[SK-007 - Báo cáo giao dịch đáng ngờ nộp quá hạn nội bộ]] - *Mức độ `Trung binh`*
- [[SK-008 - Rà soát phát hiện giá trị tài sản bảo đảm đã hết hiệu lực]] - *Mức độ `Cao`*
- [[SK-009 - Giao dịch bất thường chỉ bị phát hiện sau khi khách hàng khiếu nại]] - *Mức độ `Cao`*
- [[SK-010 - Báo cáo quản trị sử dụng dữ liệu nguồn chưa đối chiếu]] - *Mức độ `Trung binh`*
- [[SK-011 - Nhà cung cấp chậm khôi phục dịch vụ so với SLA]] - *Mức độ `Trung binh`*
- [[SK-012 - Kiểm tra sau mua sắm phát hiện thiếu kê khai xung đột lợi ích]] - *Mức độ `Trung binh`*
