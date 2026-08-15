// ==================================================
// BUỔI 14 — DEMO CYPHER QUERIES CHO MINI KNOWLEDGE GRAPH
// ==================================================

// A. Thống kê tổng số Node và Relationship của Buổi 14
MATCH (n {lab_session: 'buoi_14'})
RETURN labels(n)[0] AS NodeLabel, count(n) AS TotalCount;

MATCH ()-[r {lab_session: 'buoi_14'}]->()
RETURN type(r) AS RelType, count(r) AS TotalCount;

// B. Truy vấn cấu trúc chuỗi điều khoản (NEXT chain) của một văn bản (VD: Thông tư 01/2014)
MATCH (v:VanBan {id: '44209', lab_session: 'buoi_14'})-[:CONTAINS]->(d1:DieuKhoan)-[:NEXT]->(d2:DieuKhoan)
RETURN v.so_ky_hieu AS VanBan, d1.article AS TuDieuKhoan, d2.article AS DenDieuKhoan
LIMIT 10;

// C. Truy vấn quan hệ pháp lý 2 chặng: VanBan A -> (Rel) -> VanBan B -> CONTAINS -> DieuKhoan
MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})-[:CONTAINS]->(d:DieuKhoan)
WHERE type(r) IN ['SUA_DOI_BO_SUNG', 'CAN_CU', 'THAY_THE', 'VAN_BAN_BO_SUNG', 'HOP_NHAT']
RETURN v1.so_ky_hieu AS SourceDoc, type(r) AS RelType, v2.so_ky_hieu AS TargetDoc, d.article AS ArticleName
LIMIT 15;

// D. Kiểm tra Node mồ côi (Orphan DieuKhoan nodes không có liên kết CONTAINS với VanBan nào)
MATCH (d:DieuKhoan {lab_session: 'buoi_14'})
WHERE NOT (:VanBan)-[:CONTAINS]->(d)
RETURN count(d) AS OrphanDieuKhoanCount;
