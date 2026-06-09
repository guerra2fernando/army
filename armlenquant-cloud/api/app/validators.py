"""
Input Validators
Phase 10: Integration & Polish
"""
import re
import json
from typing import Optional, Tuple


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string input.
    
    Args:
        value: The string to sanitize
        max_length: Maximum allowed length (default 1000)
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Truncate to max length
    value = value[:max_length]
    
    # Remove potential HTML/script injection characters
    value = re.sub(r'[<>]', '', value)
    
    return value.strip()


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_task_payload(payload: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate task payload for safety and size.
    
    Args:
        payload: The task payload to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a dictionary"
    
    # Check for dangerous keys that could indicate code injection attempts
    dangerous_keys = ["__import__", "eval", "exec", "compile", "__builtins__"]
    payload_str = str(payload)
    
    for key in dangerous_keys:
        if key in payload_str:
            return False, f"Payload contains forbidden key: {key}"
    
    # Check size (100KB limit)
    try:
        payload_size = len(json.dumps(payload))
        if payload_size > 100000:
            return False, "Payload too large (max 100KB)"
    except (TypeError, ValueError) as e:
        return False, f"Payload is not JSON serializable: {e}"
    
    return True, None


def validate_agent_target(target: str) -> Tuple[bool, Optional[str]]:
    """
    Validate agent target.
    
    Args:
        target: The agent target to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_targets = [
        "ORCHESTRATOR",
        "CRYPTO_SENTINEL", 
        "JOB_HUNTER",
        "IDEAS_MACHINE",
        "META_BUILDER"
    ]
    
    if target not in valid_targets:
        return False, f"Invalid agent target. Must be one of: {', '.join(valid_targets)}"
    
    return True, None


def validate_priority(priority: int) -> Tuple[bool, Optional[str]]:
    """
    Validate task priority.
    
    Args:
        priority: Priority value (1-10)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(priority, int):
        return False, "Priority must be an integer"
    
    if priority < 1 or priority > 10:
        return False, "Priority must be between 1 and 10"
    
    return True, None


def sanitize_query_param(value: str, max_length: int = 200) -> str:
    """
    Sanitize a query parameter value.
    
    Args:
        value: The query parameter value
        max_length: Maximum allowed length
        
    Returns:
        Sanitized value
    """
    if not value:
        return ""
    
    # Remove control characters
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Truncate
    value = value[:max_length]
    
    return value.strip()

