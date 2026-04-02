import sys

sys.path.insert(0, ".")
from app.core.config import settings
from sqlalchemy import create_engine, inspect, text

try:
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    print("=" * 70)
    print("DATABASE COLUMN TYPES CHECK")
    print("=" * 70)

    with engine.connect() as conn:
        # Check mvp_knowledge_items columns
        print("\n[mvp_knowledge_items] embedding column:")
        if "mvp_knowledge_items" in inspector.get_table_names():
            columns = inspector.get_columns("mvp_knowledge_items")
            found = False
            for col in columns:
                if "embedding" in col["name"].lower():
                    print(f"  - {col['name']}: {col['type']}")
                    found = True
            if not found:
                print("  - embedding column NOT FOUND")
        else:
            print("  Table does NOT exist")

        # Check mvp_knowledge_chunks columns
        print("\n[mvp_knowledge_chunks] embedding column:")
        if "mvp_knowledge_chunks" in inspector.get_table_names():
            columns = inspector.get_columns("mvp_knowledge_chunks")
            found = False
            for col in columns:
                if "embedding" in col["name"].lower():
                    print(f"  - {col['name']}: {col['type']}")
                    found = True
            if not found:
                print("  - embedding column NOT FOUND")
        else:
            print("  Table does NOT exist")

        # Check if pgvector extension exists
        print("\n[PostgreSQL pgvector extension]:")
        result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = '''vector'''"))
        rows = result.fetchall()
        if rows:
            print(f"  pgvector: INSTALLED")
        else:
            print(f"  pgvector: NOT INSTALLED")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
