// ==================================================
// WIKI RISK GRAPH - NEO4J SCHEMA & CONSTRAINTS
// ==================================================

// 1. Unique constraint for RuiRo nodes
CREATE CONSTRAINT constraint_ruiro_id IF NOT EXISTS
FOR (r:RuiRo) REQUIRE r.id IS UNIQUE;

// 2. Unique constraint for KiemSoat nodes
CREATE CONSTRAINT constraint_kiemsoat_id IF NOT EXISTS
FOR (k:KiemSoat) REQUIRE k.id IS UNIQUE;

// 3. Unique constraint for SuKienRuiRo nodes
CREATE CONSTRAINT constraint_sukienruiro_id IF NOT EXISTS
FOR (s:SuKienRuiRo) REQUIRE s.id IS UNIQUE;
