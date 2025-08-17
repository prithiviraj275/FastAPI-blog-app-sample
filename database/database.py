# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "mysql+pymysql://root:addpassword@localhost:3306/blogapp"

# engine = create_engine(DATABASE_URL, echo=True)
# Base = declarative_base()
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 



# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL = "mysql+asyncmy://root:Raj.dk8055$@localhost:3306/blogapp"

# engine = create_async_engine(DATABASE_URL, echo=True, future=True)
# Base = declarative_base()
# AsyncSessionLocal = sessionmaker(
#     bind=engine, 
#     expire_on_commit=False, 
#     class_=AsyncSession
# )

# async def get_db():
#     async with AsyncSessionLocal() as session:
#         yield session


from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import importlib

DB_USER = "root"
DB_PASSWORD = "Raj.dk8055$"
DB_HOST = "localhost:3306"
DB_NAME = "blogapp"

# Try asyncmy first, fallback to aiomysql
if importlib.util.find_spec("asyncmy"):
    DRIVER = "asyncmy"
    print("✅ Using asyncmy driver")
else:
    DRIVER = "aiomysql"
    print("⚠ asyncmy not found — using aiomysql instead")

DATABASE_URL = f"mysql+{DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Base model
Base = declarative_base()

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
