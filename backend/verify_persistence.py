import httpx
import asyncio
import sqlite3
import json
import os
import sys
import logging

# Configuration
API_URL = "http://localhost:8000/api/chat/stream"
DB_PATH = "./data/chat_history.db"
API_KEY = "kaso_secret_key_12345"  # Matches .env

logger = logging.getLogger(__name__)

async def test_persistence():
    logger.info("🚀 Starting API Persistence Verification...")
    logger.info(f"Target URL: {API_URL}")
    logger.info(f"DB Path: {os.path.abspath(DB_PATH)}")
    
    # Check DB exists first
    if not os.path.exists(DB_PATH):
        logger.error("❌ Database file not found! Backend might not have initialized it yet.")
        return

    # 1. Send Chat Request
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Test persistence question " + str(os.urandom(4).hex()),
        "stream": True
    }
    
    logger.info(f"📤 Sending request: {payload['message']}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", API_URL, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"❌ API Error: {response.status_code} - {response.text}")
                    return

                logger.info("📥 Receiving stream...")
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if not data_str: continue
                        try:
                            data = json.loads(data_str)
                            if "token" in data:
                                full_response += data["token"]
                                sys.stdout.write(".")  # Visual feedback
                                sys.stdout.flush()
                            if "done" in data:
                                logger.info(f"\n✅ Stream done. Conv ID: {data.get('conversation_id')}")
                        except:
                            pass
                
                logger.info(f"\n📝 Full Response received.")

    except Exception as e:
        logger.exception(f"\n❌ Request Failed: {e}")
        logger.info("Is the backend running on port 8000?")
        return

    # 2. Check Database
    logger.info("\n🔍 Verifying Database Content...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check messages
        cursor.execute("SELECT role, content, created_at FROM messages ORDER BY created_at DESC LIMIT 2")
        rows = cursor.fetchall()
        
        if len(rows) >= 2:
            logger.info("✅ Found recent messages in DB:")
            for row in rows:
                logger.info(f"   - {row[0]} ({row[2]}): {row[1][:50]}...")
        else:
            logger.warning(f"❌ Database messages count low: {len(rows)}")
            
        conn.close()
        
    except Exception as e:
        logger.exception(f"❌ Database Check Failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_persistence())
