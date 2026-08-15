// ==================================================
// BUỔI 14 — MINI KNOWLEDGE GRAPH SCHEMA & CONSTRAINTS
// ==================================================

// 1. Ràng buộc Unique ID cho Node VanBan
CREATE CONSTRAINT vanban_id_unique IF NOT EXISTS
FOR (v:VanBan) REQUIRE v.id IS UNIQUE;

// 2. Ràng buộc Unique ID cho Node DieuKhoan (chunk_id)
CREATE CONSTRAINT dieukhoan_id_unique IF NOT EXISTS
FOR (d:DieuKhoan) REQUIRE d.id IS UNIQUE;

// 3. Index hỗ trợ tìm kiếm nhanh theo lab_session
CREATE INDEX vanban_lab_session_idx IF NOT EXISTS
FOR (v:VanBan) ON (v.lab_session);

CREATE INDEX dieukhoan_lab_session_idx IF NOT EXISTS
FOR (d:DieuKhoan) ON (d.lab_session);
