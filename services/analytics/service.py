from typing import List, Optional
import time
from core.background import get_background_pool
from core.config.settings import settings

async def track_query_for_crisis(tenant_id: str, query: str):
    """
    Real-time Crisis Detection logic:
    1. Extracts keywords from query.
    2. Stores keyword counts in Redis with a 1-hour window.
    3. If any keyword spike exceeds a threshold, flags a potential crisis.
    """
    # Simple keyword extraction (can be improved with LLM)
    keywords = [w.lower() for w in query.split() if len(w) > 4]
    
    redis = await get_background_pool()
    current_hour = int(time.time() // 3600)
    
    detected_crisis = []
    
    for kw in keywords:
        key = f"crisis:{tenant_id}:{current_hour}:{kw}"
        count = await redis.incr(key)
        await redis.expire(key, 3600) # Auto-cleanup
        
        # If more than 10 people ask about the same word in an hour, alert!
        if count > 10:
            detected_crisis.append(kw)
            
    return list(set(detected_crisis))
