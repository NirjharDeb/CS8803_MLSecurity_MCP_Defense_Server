# defenses/dependency_tracker.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

@dataclass
class ToolCallRecord:
    """Record of a tool call for dependency tracking."""
    tool_name: str
    timestamp: datetime
    is_read_operation: bool  # True for data-retrieval tools


class DependencyTracker:
    """
    Tracks tool call sequences to detect anomalous patterns that might
    indicate prompt injection via tool responses.
    """
    
    # Tool name patterns that indicate read/retrieval operations
    _READ_TOOL_KEYWORDS = [
        'get', 'read', 'fetch', 'retrieve', 'list', 'show', 'view',
        'download', 'load', 'query', 'search', 'find'
    ]
    
    def __init__(self, max_history: int = 10, burst_window_seconds: float = 5.0):
        self.max_history = max_history
        self.burst_window = timedelta(seconds=burst_window_seconds)
        self.call_history: List[ToolCallRecord] = []
    
    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call in the history."""
        is_read = self._is_read_operation(tool_name)
        record = ToolCallRecord(
            tool_name=tool_name,
            timestamp=datetime.now(),
            is_read_operation=is_read
        )
        
        self.call_history.append(record)
        
        # Keep only recent history
        if len(self.call_history) > self.max_history:
            self.call_history.pop(0)
    
    def check_suspicious_sequence(self, next_tool_name: str) -> tuple[bool, Optional[str]]:
        """
        Check if calling next_tool_name would create a suspicious sequence.
        
        Returns:
            (is_suspicious, reason): A tuple where is_suspicious is True if
            the sequence looks anomalous, and reason explains why.
        """
        if len(self.call_history) < 2:
            return False, None
        
        now = datetime.now()
        recent_calls = [
            record for record in self.call_history
            if now - record.timestamp < self.burst_window
        ]
        
        # Check for rapid burst of calls after a read operation
        if len(recent_calls) >= 2:
            last_call = self.call_history[-1]
            
            # If last call was a read operation, and now we have multiple
            # subsequent calls in quick succession, that's suspicious
            if last_call.is_read_operation and len(recent_calls) >= 3:
                return True, f"Rapid burst of {len(recent_calls)} tool calls after read operation"
        
        # Check for unusual escalation: read → write → write pattern
        # Only consider recent calls within the burst window
        if len(recent_calls) >= 2:
            last_two = recent_calls[-2:]
            if (last_two[0].is_read_operation and 
                not last_two[1].is_read_operation and
                not self._is_read_operation(next_tool_name)):
                return True, "Escalation from read to multiple action operations"
        
        return False, None
    
    def _is_read_operation(self, tool_name: str) -> bool:
        """Check if a tool name indicates a read/retrieval operation."""
        tool_lower = tool_name.lower()
        return any(keyword in tool_lower for keyword in self._READ_TOOL_KEYWORDS)


# Global tracker instance (one per middleware instance)
_tracker = DependencyTracker()


def record_tool_call(tool_name: str) -> None:
    """Record a tool call in the global tracker."""
    _tracker.record_tool_call(tool_name)


def check_suspicious_sequence(next_tool_name: str) -> tuple[bool, Optional[str]]:
    """Check if the next tool call would create a suspicious sequence."""
    return _tracker.check_suspicious_sequence(next_tool_name)

