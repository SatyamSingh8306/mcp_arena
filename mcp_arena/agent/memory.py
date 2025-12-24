from typing import Any, Dict, Optional, List
from collections import defaultdict
import json
from .interfaces import IAgentMemory


class SimpleMemory(IAgentMemory):
    """Simple in-memory implementation"""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
    
    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value
    
    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)
    
    def clear(self) -> None:
        self._storage.clear()


class ConversationMemory(IAgentMemory):
    """Memory optimized for conversation tracking"""
    
    def __init__(self, max_history: int = 100):
        self._storage: Dict[str, Any] = {}
        self._conversation_history: List[Dict[str, Any]] = []
        self._max_history = max_history
    
    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value
    
    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)
    
    def add_conversation_turn(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None) -> None:
        turn = {
            "user": user_input,
            "agent": agent_response,
            "metadata": metadata or {},
            "timestamp": None  # Could add actual timestamp
        }
        self._conversation_history.append(turn)
        
        # Trim history if it exceeds max length
        if len(self._conversation_history) > self._max_history:
            self._conversation_history = self._conversation_history[-self._max_history:]
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        return self._conversation_history.copy()
    
    def get_recent_context(self, num_turns: int = 5) -> str:
        recent = self._conversation_history[-num_turns:]
        context_parts = []
        for turn in recent:
            context_parts.append(f"User: {turn['user']}")
            context_parts.append(f"Agent: {turn['agent']}")
        return "\n".join(context_parts)
    
    def clear(self) -> None:
        self._storage.clear()
        self._conversation_history.clear()


class EpisodicMemory(IAgentMemory):
    """Memory that stores episodes with semantic search capabilities"""
    
    def __init__(self):
        self._episodes: List[Dict[str, Any]] = []
        self._storage: Dict[str, Any] = {}
        self._semantic_index: Dict[str, List[int]] = defaultdict(list)
    
    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value
    
    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)
    
    def add_episode(self, episode: Dict[str, Any]) -> int:
        """Add an episode and return its ID"""
        episode_id = len(self._episodes)
        episode["id"] = episode_id
        self._episodes.append(episode)
        
        # Simple keyword indexing (in real implementation, would use embeddings)
        if "content" in episode:
            words = episode["content"].lower().split()
            for word in words:
                self._semantic_index[word].append(episode_id)
        
        return episode_id
    
    def search_episodes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search episodes by content"""
        query_words = query.lower().split()
        episode_scores = defaultdict(int)
        
        for word in query_words:
            for episode_id in self._semantic_index.get(word, []):
                episode_scores[episode_id] += 1
        
        # Sort by score and return top episodes
        sorted_episodes = sorted(
            episode_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [self._episodes[ep_id] for ep_id, _ in sorted_episodes[:limit]]
    
    def get_episode(self, episode_id: int) -> Optional[Dict[str, Any]]:
        if 0 <= episode_id < len(self._episodes):
            return self._episodes[episode_id]
        return None
    
    def clear(self) -> None:
        self._storage.clear()
        self._episodes.clear()
        self._semantic_index.clear()


class MemoryFactory:
    """Factory for creating different types of memory"""
    
    @staticmethod
    def create_memory(memory_type: str, **kwargs) -> IAgentMemory:
        if memory_type == "simple":
            return SimpleMemory()
        elif memory_type == "conversation":
            return ConversationMemory(kwargs.get("max_history", 100))
        elif memory_type == "episodic":
            return EpisodicMemory()
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")