import asyncio
import os
import sys
import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Setup path
sys.path.append(os.getcwd())

# Configuration
DB_PATH = "./data/chat_history.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

logger = logging.getLogger(__name__)

async def check_db():
    logger.info(f"🔍 Checking database at: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        logger.error("❌ Database file not found!")
        return

    try:
        engine = create_async_engine(DB_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session() as session:
            logger.info("✅ Connection established.")
            
            # Check tables
            try:
                # Count conversations
                result = await session.execute(text("SELECT COUNT(*) FROM conversations"))
                conv_count = result.scalar()
                logger.info(f"📊 Conversations count: {conv_count}")
                
                # Count messages
                result = await session.execute(text("SELECT COUNT(*) FROM messages"))
                msg_count = result.scalar()
                logger.info(f"📊 Messages count: {msg_count}")
                
                # Check recent messages
                if msg_count > 0:
                    result = await session.execute(text("SELECT content, created_at FROM messages ORDER BY created_at DESC LIMIT 3"))
                    logger.info("\n📝 Recent messages:")
                    for row in result:
                        logger.info(f"   - [{row[1]}] {row[0][:50]}...")
                
                # Test Write
                logger.info("\n🧪 Testing write permission...")
                await session.execute(text("CREATE TABLE IF NOT EXISTS debug_test (id INTEGER PRIMARY KEY)"))
                await session.execute(text("INSERT INTO debug_test DEFAULT VALUES"))
                await session.commit()
                logger.info("✅ Write successful.")
                
            except Exception as e:
                logger.exception(f"❌ Database Query Error: {e}")
                
    except Exception as e:
        logger.exception(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_db())
