from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./air_pollution.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def migrate_database():
    """迁移数据库，添加新字段"""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE meteorology ADD COLUMN cloud_cover REAL DEFAULT 0.0"))
            print("✓ 添加 cloud_cover 字段")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"✗ 添加 cloud_cover 失败: {e}")
        
        try:
            conn.execute(text("ALTER TABLE meteorology ADD COLUMN precipitation REAL DEFAULT 0.0"))
            print("✓ 添加 precipitation 字段")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"✗ 添加 precipitation 失败: {e}")
        
        conn.commit()
    
    print("数据库迁移完成！")

if __name__ == "__main__":
    migrate_database()
