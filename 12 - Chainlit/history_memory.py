import hashlib
import base64
import logging
from threading import Lock
from typing import Dict, Optional, List, Tuple, Any
from semantic_kernel.agents import ChatHistoryAgentThread
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

class HistoryMemory:
    """
    Manages chat history for users across different conversations.
    This class stores and retrieves conversation history for the AI agent.
    """
    
    def __init__(self, expiration_minutes: int = 60):
        """
        Initialize the HistoryMemory with an empty dictionary to store chat histories.
        
        Args:
            expiration_minutes: The number of minutes after which a chat history is considered expired.
        """
        # Store as tuple of (ChatHistoryAgentThread, timestamp)
        self._chat_histories: Dict[str, Tuple[ChatHistoryAgentThread, datetime]] = {}
        self._lock = Lock()  # Thread safety mechanism
        self._expiration_minutes = expiration_minutes

    def get_or_create_history(self, user_id: str, discussion_id: str) -> ChatHistoryAgentThread:
        """
        Gets an existing chat history for a user and discussion or creates a new one.
        
        Args:
            user_id: The ID of the user.
            discussion_id: The ID of the discussion.
            
        Returns:
            The chat history thread.
        """
        key = self._generate_dictionary_key(user_id, discussion_id)
        
        with self._lock:
            if key not in self._chat_histories or self._is_expired(self._chat_histories[key][1]):
                logger.info(f"Creating new chat history for user {user_id} and discussion {discussion_id}")
                # Create a new empty thread - we don't need to initialize with system prompt
                # as that will be handled by the agent during invoke
                thread = ChatHistoryAgentThread()
                self._chat_histories[key] = (thread, datetime.now())
            else:
                logger.info(f"Retrieved existing chat history from cache for user {user_id} and discussion {discussion_id}")
            
            return self._chat_histories[key][0]

    def update_history(self, user_id: str, discussion_id: str, thread: ChatHistoryAgentThread) -> bool:
        """
        Updates the chat history for a user and discussion.
        
        Args:
            user_id: The ID of the user.
            discussion_id: The ID of the discussion.
            thread: The updated chat history thread.
            
        Returns:
            True if the history was updated, False if it wasn't found.
        """
        key = self._generate_dictionary_key(user_id, discussion_id)
        with self._lock:
            if key in self._chat_histories:
                self._chat_histories[key] = (thread, datetime.now())
                return True
            return False
    
    def _generate_dictionary_key(self, user_id: str, discussion_id: str) -> str:
        """
        Generates a dictionary key for the chat history using a hash function.
        
        Args:
            user_id: The ID of the user.
            discussion_id: The ID of the discussion.
            
        Returns:
            A string key for the chat histories dictionary.
        """
        input_string = f"{user_id}:{discussion_id}"
        hash_bytes = hashlib.sha256(input_string.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')

    def get_all_keys(self) -> List[str]:
        """
        Returns all keys in the chat histories dictionary.
        
        Returns:
            A list of all keys.
        """
        with self._lock:
            return list(self._chat_histories.keys())
    
    def clear_history(self, user_id: str, discussion_id: str) -> bool:
        """
        Clears the chat history for a user and discussion.
        
        Args:
            user_id: The ID of the user.
            discussion_id: The ID of the discussion.
            
        Returns:
            True if the history was cleared, False if it wasn't found.
        """
        key = self._generate_dictionary_key(user_id, discussion_id)
        with self._lock:
            if key in self._chat_histories:
                del self._chat_histories[key]
                return True
            return False

    def get_history_stats(self) -> Dict[str, int]:
        """
        Returns statistics about the chat histories cache.
        
        Returns:
            A dictionary containing statistics about the chat histories cache.
        """
        with self._lock:
            return {
                "total_histories": len(self._chat_histories),
                "memory_usage_estimate": sum(len(str(thread)) for thread, _ in self._chat_histories.values())
            }

    def _is_expired(self, timestamp: datetime) -> bool:
        """
        Checks if a given timestamp is expired based on the expiration time.
        
        Args:
            timestamp: The timestamp to check.
            
        Returns:
            True if the timestamp is expired, False otherwise.
        """
        return datetime.now() - timestamp > timedelta(minutes=self._expiration_minutes)

    def clean_expired_histories(self) -> None:
        """
        Cleans up expired chat histories from the cache.
        """
        with self._lock:
            keys_to_delete = [key for key, (_, timestamp) in self._chat_histories.items() if self._is_expired(timestamp)]
            for key in keys_to_delete:
                del self._chat_histories[key]    
    def get_detailed_cache_info(self) -> Dict[str, Any]:
        """
        Returns detailed information about the chat histories cache.
        
        Returns:
            A dictionary containing detailed information about the chat histories cache.
        """
        with self._lock:
            oldest = None
            newest = None
            total_size = 0
            
            if self._chat_histories:
                timestamps = [ts for _, ts in self._chat_histories.values()]
                oldest = min(timestamps)
                newest = max(timestamps)
                total_size = sum(len(str(thread)) for thread, _ in self._chat_histories.values())
            
            return {
                "total_histories": len(self._chat_histories),
                "total_memory_usage_estimate": total_size,
                "oldest_entry": oldest.isoformat() if oldest else None,
                "newest_entry": newest.isoformat() if newest else None,
                "cache_expiration_minutes": self._expiration_minutes,
                "expired_entries": sum(1 for _, timestamp in self._chat_histories.values() if self._is_expired(timestamp))
            }
