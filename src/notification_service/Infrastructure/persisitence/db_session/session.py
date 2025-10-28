"""
    Database configuration and connection management
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

import logging 
from typing import Optional

logger = logging.getLogger(__name__)

# MetaData for table creation 
metadata = MetaData()
Base = declarative_base()

class Database:
    """Database connection manager using SQLAlchemy AsyncSession"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_maker: Optional[async_sessionmaker] = None
        
        
    async def get_session(self) -> AsyncSession:
        """Get a  database session"""
        if not self.session_maker:
         raise RuntimeError("Database session maker is not initialized.")
         
        return self.session_maker()

    async def connect(self):
        """Initialize the database (create tables)"""
        try:
            logger.info("Initializing database...")
            
            #create async engine
            self.engine = create_async_engine(self.database_url, echo=True)
            
            #create session maker
            self.session_maker = async_sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
            
            #test connection
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: None)
            logger.info("Database connection established successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
            
    async def disconnect(self):
        """Dispose the database engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection disposed.")
    
    async def create_db(self):
        """Create all tables in the database"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully.")

    async def drop_db(self):
        """Drop all tables in the database"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully.")
            
# Global database instance (will be initialized in application startup)
database: Optional[Database] = None


async def get_database() -> Database:
    """Dependency to get the database instance"""
    if not database:
        raise RuntimeError("Database is not initialized.")
    return database
    

async def get_db_session() -> AsyncSession:
    """Dependency to get a database session"""
    db = await get_database()
    async with db.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
        