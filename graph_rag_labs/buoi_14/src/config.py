import os
from dotenv import load_dotenv

# Path to .env file in buoi_14 directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Load environment variables
load_dotenv(ENV_PATH)

# ==============================================================================
# RBAC ROLES CONFIGURATION
# ==============================================================================
ROLES = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]

# Role hierarchy / permissions matrix (which roles can view items tagged with allowed_roles)
ROLE_HIERARCHY = {
    "Admin": ["Admin", "HR", "Risk_Manager", "Staff", "Guest"],
    "HR": ["HR", "Staff", "Guest"],
    "Risk_Manager": ["Risk_Manager", "Staff", "Guest"],
    "Staff": ["Staff", "Guest"],
    "Guest": ["Guest"]
}

# ==============================================================================
# NEO4J DATABASE CONFIGURATION
# ==============================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "abcd1234")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
