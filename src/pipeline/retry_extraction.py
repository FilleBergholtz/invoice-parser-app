"""Retry logic for extraction with different strategies to improve confidence scores."""

from typing import Callable, Optional, Tuple, Any, Dict
from functools import wraps
import time


def retry_extraction(
    target_confidence: float,
    max_attempts: int = 5,
    strategy_variations: Optional[list] = None
) -> Callable:
    """Decorator for extraction functions to retry with different strategies.
    
    Args:
        target_confidence: Minimum confidence score to achieve (0.0-1.0)
        max_attempts: Maximum number of retry attempts (default 5)
        strategy_variations: List of strategy variations to try (e.g., different patterns)
        
    Returns:
        Decorated function that retries extraction with different strategies
        
    Usage:
        @retry_extraction(target_confidence=0.95, max_attempts=5)
        def extract_invoice_number(header_segment, invoice_header, strategy=None):
            # strategy parameter will be passed by retry decorator
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we already have a strategy parameter
            has_strategy = 'strategy' in kwargs or (len(args) > 0 and hasattr(args[0], 'strategy'))
            
            # If no strategy variations provided, create default ones
            if strategy_variations is None:
                strategies = [None, 'aggressive', 'conservative', 'extended_patterns', 'broader_search']
            else:
                strategies = strategy_variations
            
            best_result = None
            best_confidence = 0.0
            attempts = []
            
            for attempt_num in range(max_attempts):
                # Select strategy for this attempt
                strategy = strategies[attempt_num % len(strategies)] if strategies else None
                
                # Call extraction function with strategy
                try:
                    if 'strategy' in kwargs:
                        kwargs['strategy'] = strategy
                    elif len(args) > 0 and hasattr(args[0], '__dict__'):
                        # Try to add strategy to first arg if it's an object
                        pass  # Strategy will be passed via kwargs
                    else:
                        kwargs['strategy'] = strategy
                    
                    # Call the extraction function
                    result = func(*args, **kwargs)
                    
                    # Extract confidence from result
                    # Assume result is an object with confidence attribute or dict with confidence key
                    if hasattr(result, 'confidence'):
                        confidence = result.confidence
                    elif isinstance(result, dict) and 'confidence' in result:
                        confidence = result['confidence']
                    elif len(args) > 0 and hasattr(args[-1], 'invoice_number_confidence'):
                        # For invoice number extraction, check invoice_header
                        invoice_header = args[-1]
                        confidence = invoice_header.invoice_number_confidence
                    elif len(args) > 0 and hasattr(args[-1], 'total_confidence'):
                        # For total amount extraction, check invoice_header
                        invoice_header = args[-1]
                        confidence = invoice_header.total_confidence
                    else:
                        confidence = 0.0
                    
                    attempts.append({
                        'attempt': attempt_num + 1,
                        'strategy': strategy,
                        'confidence': confidence,
                        'success': confidence >= target_confidence
                    })
                    
                    # Track best result
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_result = result
                    
                    # If we reached target confidence, return early
                    if confidence >= target_confidence:
                        return result
                        
                except Exception as e:
                    attempts.append({
                        'attempt': attempt_num + 1,
                        'strategy': strategy,
                        'confidence': 0.0,
                        'success': False,
                        'error': str(e)
                    })
                    continue
            
            # Return best result even if target not reached
            return best_result
            
        return wrapper
    return decorator


def extract_with_retry(
    extract_func: Callable,
    target_confidence: float,
    max_attempts: int = 5,
    strategy_variations: Optional[list] = None,
    progress_callback: Optional[Callable[[str, float, int], None]] = None
) -> Tuple[Any, float, list]:
    """Extract with retry logic and different strategies.
    
    Args:
        extract_func: Extraction function to call (should accept 'strategy' parameter)
        target_confidence: Minimum confidence score to achieve
        max_attempts: Maximum number of retry attempts
        strategy_variations: List of strategy variations to try
        progress_callback: Optional callback function(status_message, confidence, attempt_num)
        
    Returns:
        Tuple of (result, final_confidence, attempts_list)
    """
    if strategy_variations is None:
        strategies = [None, 'aggressive', 'conservative', 'extended_patterns', 'broader_search']
    else:
        strategies = strategy_variations
    
    best_result = None
    best_confidence = 0.0
    attempts = []
    
    for attempt_num in range(max_attempts):
        strategy = strategies[attempt_num % len(strategies)] if strategies else None
        
        if progress_callback:
            progress_callback(
                f"Försök {attempt_num + 1}/{max_attempts} (strategi: {strategy or 'standard'})",
                best_confidence,
                attempt_num + 1
            )
        
        try:
            # Call extraction function with strategy
            result = extract_func(strategy=strategy)
            
            # Extract confidence (assumes result has confidence attribute or is dict)
            if hasattr(result, 'confidence'):
                confidence = result.confidence
            elif isinstance(result, dict) and 'confidence' in result:
                confidence = result['confidence']
            else:
                confidence = 0.0
            
            attempts.append({
                'attempt': attempt_num + 1,
                'strategy': strategy,
                'confidence': confidence,
                'success': confidence >= target_confidence
            })
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_result = result
            
            if confidence >= target_confidence:
                if progress_callback:
                    progress_callback(
                        f"✓ Uppnådde {target_confidence*100:.0f}% confidence på försök {attempt_num + 1}",
                        confidence,
                        attempt_num + 1
                    )
                return result, confidence, attempts
                
        except Exception as e:
            attempts.append({
                'attempt': attempt_num + 1,
                'strategy': strategy,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            })
            continue
    
    # Return best result even if target not reached
    if progress_callback:
        progress_callback(
            f"⚠ Bästa confidence: {best_confidence*100:.1f}% (mål: {target_confidence*100:.0f}%)",
            best_confidence,
            max_attempts
        )
    return best_result, best_confidence, attempts
