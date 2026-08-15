// ==================================================
// WIKI RISK GRAPH - DEMO CYPHER QUERIES
// ==================================================

// A. Xem toàn bộ graph (Nodes & Relationships)
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;

// B. Tìm kiểm soát giảm thiểu một rủi ro cụ thể (VD: RR-001)
MATCH (c:KiemSoat)-[r:MITIGATES]->(rr:RuiRo {id: 'RR-001'})
RETURN c.id AS ControlID, c.name AS ControlName, r.evidence_quote AS Evidence, rr.id AS RiskID, rr.name AS RiskName;

// C. Tìm tất cả sự kiện rủi ro của một rủi ro cụ thể (VD: RR-001)
MATCH (rr:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(e:SuKienRuiRo)
RETURN rr.id AS RiskID, rr.name AS RiskName, r.relationship_type AS RelType, e.id AS EventID, e.description AS EventDescription;

// D. Tìm đường liên kết 3 chặng: KiemSoat -> RuiRo -> SuKienRuiRo
MATCH path = (c:KiemSoat)-[:MITIGATES]->(rr:RuiRo)-[:OBSERVED_AS]->(e:SuKienRuiRo)
RETURN path;

// E. Tìm các rủi ro KHÔNG CÓ bất kỳ kiểm soát giảm thiểu nào (Unmitigated Risks)
MATCH (rr:RuiRo)
WHERE NOT (:KiemSoat)-[:MITIGATES]->(rr)
RETURN rr.id AS RiskID, rr.name AS RiskName, rr.category AS Category, rr.inherent_level AS InherentLevel;

// F. Tìm tất cả các quan hệ chưa được xác minh (VERIFICATION_STATUS <> 'VERIFIED')
MATCH (a)-[r]->(b)
WHERE r.verification_status <> 'VERIFIED'
RETURN a.id AS SourceID, type(r) AS RelType, b.id AS TargetID, r.verification_status AS Status;
