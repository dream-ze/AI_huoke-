"""检查 embedding 列类型"""
from app.core.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 检查 embedding 列
    result = conn.execute(text("""
        SELECT table_name, column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE column_name = 'embedding' AND table_name LIKE 'mvp_%'
    """))
    rows = list(result)
    print("=== Embedding 列类型 ===")
    for row in rows:
        print(f'{row[0]}.{row[1]}: data_type={row[2]}, udt_name={row[3]}')
    if not rows:
        print('No embedding columns found in mvp_* tables')
    
    # 检查 pg_extension
    print("\n=== 已安装扩展 ===")
    result = conn.execute(text("SELECT extname, extversion FROM pg_extension"))
    for row in result:
        print(f'{row[0]}: {row[1]}')
