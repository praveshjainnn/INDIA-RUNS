"""RecruiterIQ — Central Configuration"""
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "[PUB] India_runs_data_and_ai_challenge" / "India_runs_data_and_ai_challenge"
CANDIDATES_JSONL = DATA_DIR / "candidates.jsonl"
JD_DOCX = DATA_DIR / "job_description.docx"
SAMPLE_CANDIDATES = DATA_DIR / "sample_candidates.json"
OUTPUT_CSV = DATA_DIR / "submission.csv"

# ── Embedding Model ───────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ── Scoring Weights (must sum to 1.0) ────────────────────────────────────────
WEIGHTS = {
    "skill_alignment": 0.30,
    "experience_relevance": 0.25,
    "career_signal": 0.20,
    "behavioral_fit": 0.15,
    "cultural_alignment": 0.10,
}

# ── Score Thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "strong_match": 90,
    "good_match": 75,
    "possible": 60,
}

# ── Tier Labels ───────────────────────────────────────────────────────────────
TIER_LABELS = {
    "strong_match": "Strong Match",
    "good_match": "Good Match",
    "possible": "Possible",
    "stretch": "Stretch",
}

TIER_COLORS = {
    "strong_match": "#22C55E",
    "good_match": "#4F6EF7",
    "possible": "#F59E0B",
    "stretch": "#9CA3AF",
}

# ── Pipeline Settings ─────────────────────────────────────────────────────────
# Fast-path: pure-Python scorer narrows field before embedding
FAST_PATH_TOP_N = 500      # Score all, take top-N for embedding
SHORTLIST_SIZE = 100       # Final ranked shortlist size for submission
DISPLAY_DEFAULT = 10       # Cards shown by default in UI

# ── Skill Taxonomy ────────────────────────────────────────────────────────────
# Broad set of tech skills for JD parsing & semantic matching
TECH_SKILLS = [
    # ML / AI core
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "supervised learning",
    "unsupervised learning", "transfer learning", "fine-tuning", "lora", "qlora", "peft",
    # LLM / GenAI
    "llm", "large language model", "gpt", "bert", "transformers", "hugging face",
    "langchain", "llamaindex", "rag", "retrieval augmented generation",
    # Search / Retrieval
    "embeddings", "sentence transformers", "vector db", "vector database",
    "retrieval", "semantic search", "hybrid search", "dense retrieval",
    "bm25", "faiss", "milvus", "pinecone", "weaviate", "qdrant",
    "elasticsearch", "opensearch", "solr",
    # ML Ops / Engineering
    "mlops", "ml pipeline", "feature pipeline", "feature engineering",
    "feature store", "model serving", "model deployment", "model monitoring",
    "a/b testing", "evaluation", "ndcg", "mrr", "map",
    # Frameworks
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
    "xgboost", "lightgbm", "catboost", "spark ml", "pyspark",
    # Data Engineering
    "spark", "pyspark", "hadoop", "kafka", "airflow", "dbt", "flink",
    "databricks", "snowflake", "redshift", "bigquery", "hive",
    # Languages
    "python", "scala", "java", "sql", "r", "julia", "go",
    # Cloud / Infra
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform",
    "mlflow", "kubeflow", "sagemaker", "vertex ai",
    # APIs / Backend
    "fastapi", "flask", "django", "grpc", "rest api",
    # Data Science tools
    "pandas", "numpy", "scipy", "matplotlib", "plotly",
]

BEHAVIORAL_SIGNALS = [
    "ownership", "cross-functional", "scale", "impact", "leadership",
    "collaboration", "mentoring", "initiative", "autonomous", "self-starter",
    "data-driven", "problem solving", "communication", "stakeholder",
    "ambiguity", "fast-paced", "startup", "product mindset",
]

# ── Location ─────────────────────────────────────────────────────────────────
TIER1_CITIES = {
    "pune", "noida", "delhi", "ncr", "gurugram", "gurgaon",
    "mumbai", "bengaluru", "bangalore", "hyderabad", "chennai",
}
