from typing import Optional, Any, Dict, List
import json
import pickle
import logging
from datetime import datetime, timedelta
import asyncio
import uuid
import redis.asyncio as redis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager and utilities"""
    
    def __init__(self):
        self._redis_client: Optional[Redis] = None
        self._is_connected = False
    
    async def connect(self, redis_url: str) -> None:
        """Establish Redis connection"""
        try:
            self._redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding/decoding manually
                max_connections=20,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis_client.ping()
            self._is_connected = True
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._is_connected = False
            logger.info("Redis connection closed")
    
    @property
    def client(self) -> Redis:
        """Get Redis client"""
        if not self._is_connected or not self._redis_client:
            raise RuntimeError("Redis is not connected")
        return self._redis_client
    
    async def is_healthy(self) -> bool:
        """Check Redis health"""
        try:
            if self._redis_client:
                await self._redis_client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        return False


# Global Redis manager instance
redis_manager = RedisManager()


class CacheService:
    """Service for caching operations"""
    
    DEFAULT_TTL = 3600  # 1 hour
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # Try to deserialize as JSON first, then as pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                try:
                    return pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    return value.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serialize_as: str = "json"
    ) -> bool:
        """Set value in cache"""
        try:
            if ttl is None:
                ttl = self.DEFAULT_TTL
            
            # Serialize value
            if serialize_as == "json":
                serialized_value = json.dumps(value, default=str).encode('utf-8')
            elif serialize_as == "pickle":
                serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value).encode('utf-8')
            
            result = await self.redis.setex(key, ttl, serialized_value)
            return result
        
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            result = await self.redis.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode('utf-8') for key in keys]
        except Exception as e:
            logger.error(f"Cache keys error for pattern {pattern}: {e}")
            return []
    
    async def flush_all(self) -> bool:
        """Flush all keys from cache"""
        try:
            await self.redis.flushall()
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False


class SessionService:
    """Service for session management"""
    
    SESSION_TTL = 86400  # 24 hours
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def create_session(
        self, 
        session_id: str, 
        user_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Create new session"""
        try:
            session_data = {
                "session_id": session_id,
                "user_data": user_data,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "is_active": True
            }
            
            key = f"session:{session_id}"
            return await self.redis.setex(key, self.SESSION_TTL, json.dumps(session_data))
        
        except Exception as e:
            logger.error(f"Session create error: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            key = f"session:{session_id}"
            value = await self.redis.get(key)
            
            if value is None:
                return None
            
            session_data = json.loads(value.decode('utf-8'))
            
            # Update last accessed time
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            await self.redis.setex(key, self.SESSION_TTL, json.dumps(session_data))
            
            return session_data
        
        except Exception as e:
            logger.error(f"Session get error: {e}")
            return None
    
    async def update_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Update session user data"""
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return False
            
            session_data["user_data"] = user_data
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            
            key = f"session:{session_id}"
            return await self.redis.setex(key, self.SESSION_TTL, json.dumps(session_data))
        
        except Exception as e:
            logger.error(f"Session update error: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        try:
            key = f"session:{session_id}"
            result = await self.redis.delete(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Session delete error: {e}")
            return False
    
    async def is_session_valid(self, session_id: str) -> bool:
        """Check if session is valid"""
        try:
            session_data = await self.get_session(session_id)
            return session_data is not None and session_data.get("is_active", False)
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            pattern = f"session:*"
            keys = await self.redis.keys(pattern)
            
            user_sessions = []
            for key in keys:
                session_id = key.decode('utf-8').split(":")[1]
                session_data = await self.get_session(session_id)
                
                if session_data and session_data.get("user_data", {}).get("sub") == user_id:
                    user_sessions.append(session_data)
            
            return user_sessions
        
        except Exception as e:
            logger.error(f"Get user sessions error: {e}")
            return []
    
    async def revoke_user_sessions(self, user_id: str, exclude_session: Optional[str] = None) -> int:
        """Revoke all sessions for a user"""
        try:
            pattern = f"session:*"
            keys = await self.redis.keys(pattern)
            
            revoked_count = 0
            for key in keys:
                session_id = key.decode('utf-8').split(":")[1]
                
                if exclude_session and session_id == exclude_session:
                    continue
                
                session_data = await self.get_session(session_id)
                if session_data and session_data.get("user_data", {}).get("sub") == user_id:
                    await self.delete_session(session_id)
                    revoked_count += 1
            
            return revoked_count
        
        except Exception as e:
            logger.error(f"Revoke user sessions error: {e}")
            return 0


class RateLimitService:
    """Service for rate limiting"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: int,
        identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if request is allowed based on rate limit"""
        try:
            if identifier:
                rate_limit_key = f"rate_limit:{key}:{identifier}"
            else:
                rate_limit_key = f"rate_limit:{key}"
            
            # Use sliding window approach
            current_time = datetime.utcnow().timestamp()
            window_start = current_time - window
            
            # Remove old entries
            await self.redis.zremrangebyscore(rate_limit_key, 0, window_start)
            
            # Get current count
            current_count = await self.redis.zcard(rate_limit_key)
            
            if current_count >= limit:
                # Get oldest request time for retry_after
                oldest_request = await self.redis.zrange(rate_limit_key, 0, 0, withscores=True)
                retry_after = 0
                
                if oldest_request:
                    oldest_time = oldest_request[0][1]
                    retry_after = int(window_start + window - oldest_time)
                
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": int(current_time + window),
                    "retry_after": max(retry_after, 0)
                }
            
            # Add current request
            await self.redis.zadd(rate_limit_key, {str(current_time): current_time})
            await self.redis.expire(rate_limit_key, window)
            
            remaining = limit - current_count - 1
            
            return {
                "allowed": True,
                "limit": limit,
                "remaining": remaining,
                "reset_time": int(current_time + window),
                "retry_after": 0
            }
        
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request on error
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(datetime.utcnow().timestamp() + window),
                "retry_after": 0
            }
    
    async def get_rate_limit_status(self, key: str, identifier: Optional[str] = None) -> Dict[str, Any]:
        """Get current rate limit status"""
        try:
            if identifier:
                rate_limit_key = f"rate_limit:{key}:{identifier}"
            else:
                rate_limit_key = f"rate_limit:{key}"
            
            # Get current count and oldest request
            current_count = await self.redis.zcard(rate_limit_key)
            oldest_request = await self.redis.zrange(rate_limit_key, 0, 0, withscores=True)
            
            current_time = datetime.utcnow().timestamp()
            
            if oldest_request:
                oldest_time = oldest_request[0][1]
                ttl = await self.redis.ttl(rate_limit_key)
                reset_time = int(current_time + ttl) if ttl > 0 else int(current_time)
            else:
                reset_time = int(current_time)
            
            return {
                "current_count": current_count,
                "reset_time": reset_time
            }
        
        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {
                "current_count": 0,
                "reset_time": int(datetime.utcnow().timestamp())
            }


class LockService:
    """Service for distributed locks"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def acquire_lock(
        self, 
        lock_key: str, 
        timeout: int = 30,
        retry_delay: float = 0.1,
        max_retries: int = 30
    ) -> Optional[str]:
        """Acquire distributed lock"""
        try:
            lock_value = str(uuid.uuid4())
            lock_key_full = f"lock:{lock_key}"
            
            for attempt in range(max_retries):
                # Try to acquire lock with SETNX + EXPIRE
                result = await self.redis.set(
                    lock_key_full, 
                    lock_value, 
                    ex=timeout, 
                    nx=True
                )
                
                if result:
                    return lock_value
                
                # Wait before retry
                await asyncio.sleep(retry_delay)
            
            return None
        
        except Exception as e:
            logger.error(f"Lock acquire error: {e}")
            return None
    
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """Release distributed lock"""
        try:
            lock_key_full = f"lock:{lock_key}"
            
            # Use Lua script for atomic release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, lock_key_full, lock_value)
            return result > 0
        
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False
    
    async def is_locked(self, lock_key: str) -> bool:
        """Check if lock exists"""
        try:
            lock_key_full = f"lock:{lock_key}"
            return await self.redis.exists(lock_key_full) > 0
        except Exception as e:
            logger.error(f"Lock check error: {e}")
            return False


class PubSubService:
    """Service for Redis pub/sub messaging"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._pubsub = None
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish message to channel"""
        try:
            message_json = json.dumps(message, default=str)
            result = await self.redis.publish(channel, message_json)
            return result > 0
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False
    
    async def subscribe(self, channels: List[str]):
        """Subscribe to channels"""
        try:
            self._pubsub = self.redis.pubsub()
            await self._pubsub.subscribe(*channels)
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            raise
    
    async def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get message from subscribed channels"""
        try:
            if not self._pubsub:
                raise RuntimeError("Not subscribed to any channels")
            
            message = await self._pubsub.get_message(timeout=timeout)
            
            if message and message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    return {
                        'channel': message['channel'],
                        'data': data
                    }
                except json.JSONDecodeError:
                    return {
                        'channel': message['channel'],
                        'data': message['data']
                    }
            
            return None
        except Exception as e:
            logger.error(f"Get message error: {e}")
            return None
    
    async def unsubscribe(self, channels: Optional[List[str]] = None):
        """Unsubscribe from channels"""
        try:
            if self._pubsub:
                if channels:
                    await self._pubsub.unsubscribe(*channels)
                else:
                    await self._pubsub.unsubscribe()
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")


# Service instances
cache_service: Optional[CacheService] = None
session_service: Optional[SessionService] = None
rate_limit_service: Optional[RateLimitService] = None
lock_service: Optional[LockService] = None
pubsub_service: Optional[PubSubService] = None


async def init_redis_services(redis_url: str) -> None:
    """Initialize all Redis services"""
    global cache_service, session_service, rate_limit_service, lock_service, pubsub_service
    
    await redis_manager.connect(redis_url)
    
    cache_service = CacheService(redis_manager.client)
    session_service = SessionService(redis_manager.client)
    rate_limit_service = RateLimitService(redis_manager.client)
    lock_service = LockService(redis_manager.client)
    pubsub_service = PubSubService(redis_manager.client)
    
    logger.info("Redis services initialized")


async def close_redis_services() -> None:
    """Close all Redis services"""
    await redis_manager.disconnect()
    logger.info("Redis services closed")
