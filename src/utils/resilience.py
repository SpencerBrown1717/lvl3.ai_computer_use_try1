"""
Resilience utilities for Computer Control Agent
Provides retry mechanisms, circuit breakers, and other resilience patterns
"""

import time
import logging
import functools
import random
from typing import Callable, Any, Dict, List, Optional, Union, TypeVar

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('resilience')

# Type variable for generic function return type
T = TypeVar('T')

class RetryWithExponentialBackoff:
    """
    Retry mechanism with exponential backoff
    
    Implements a retry strategy that increases the delay between attempts
    exponentially, with optional jitter to prevent thundering herd problems.
    """
    
    def __init__(
        self, 
        max_attempts: int = 3, 
        initial_delay: float = 1.0, 
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        exceptions: tuple = (Exception,)
    ):
        """
        Initialize the retry mechanism
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between attempts in seconds
            backoff_factor: Multiplier for delay after each attempt
            jitter: Random jitter factor to add to delay (0-1)
            exceptions: Tuple of exceptions to catch and retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The return value of the function
            
        Raises:
            The last exception if all attempts fail
        """
        attempt = 0
        delay = self.initial_delay
        last_exception = None
        
        while attempt < self.max_attempts:
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                attempt += 1
                last_exception = e
                
                if attempt >= self.max_attempts:
                    break
                
                # Calculate delay with jitter
                jitter_amount = random.uniform(-self.jitter, self.jitter)
                adjusted_delay = delay * (1 + jitter_amount)
                
                logger.warning(f"Attempt {attempt}/{self.max_attempts} failed: {e}. Retrying in {adjusted_delay:.2f}s")
                time.sleep(adjusted_delay)
                
                # Increase delay for next attempt
                delay *= self.backoff_factor
        
        # If we get here, all attempts failed
        logger.error(f"All {self.max_attempts} attempts failed. Last error: {last_exception}")
        raise last_exception

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures
    
    The circuit breaker has three states:
    - CLOSED: All requests go through normally
    - OPEN: All requests fail fast without executing the function
    - HALF_OPEN: A limited number of test requests are allowed through
    
    If too many failures occur in a short time, the circuit opens and
    requests fail fast. After a timeout, the circuit goes to half-open
    to test if the underlying issue is resolved.
    """
    
    # Circuit states
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: float = 30.0,
        test_requests: int = 1
    ):
        """
        Initialize the circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before attempting recovery
            test_requests: Number of test requests to allow when half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.test_requests = test_requests
        
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.test_requests_remaining = 0
        
    def __call__(self, func: Callable[..., T]) -> Callable[..., Optional[T]]:
        """
        Decorator to apply circuit breaker to a function
        
        Args:
            func: The function to wrap with circuit breaker
            
        Returns:
            Wrapped function with circuit breaker logic
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            return self._call(func, *args, **kwargs)
        return wrapper
        
    def _call(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """
        Execute the function with circuit breaker logic
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function or None if circuit is open
        """
        if self.state == self.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit half-open, allowing {self.test_requests} test requests")
                self.state = self.HALF_OPEN
                self.test_requests_remaining = self.test_requests
            else:
                logger.warning(f"Circuit open, failing fast (retry after {self.recovery_timeout - (time.time() - self.last_failure_time):.1f}s)")
                return None
                
        if self.state == self.HALF_OPEN and self.test_requests_remaining <= 0:
            logger.warning("No test requests remaining, failing fast")
            return None
            
        try:
            result = func(*args, **kwargs)
            
            # Success, reset circuit if needed
            if self.state == self.HALF_OPEN:
                logger.info("Test request succeeded, closing circuit")
                self.state = self.CLOSED
                self.failure_count = 0
                
            return result
            
        except Exception as e:
            self._handle_failure(e)
            return None
            
    def _handle_failure(self, exception: Exception) -> None:
        """
        Handle a function failure
        
        Args:
            exception: The exception that occurred
        """
        if self.state == self.CLOSED:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                logger.warning(f"Failure threshold reached ({self.failure_count}/{self.failure_threshold}), opening circuit")
                self.state = self.OPEN
                self.last_failure_time = time.time()
                
        elif self.state == self.HALF_OPEN:
            logger.warning("Test request failed, reopening circuit")
            self.state = self.OPEN
            self.last_failure_time = time.time()
            
        logger.error(f"Operation failed: {str(exception)}")

def retry(
    max_attempts: int = 3, 
    delay: float = 1.0, 
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff_factor: Multiplier for delay after each attempt
        jitter: Random jitter factor to add to delay (0-1)
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # Calculate jitter
                        jitter_value = random.uniform(-jitter * current_delay, jitter * current_delay)
                        sleep_time = current_delay + jitter_value
                        
                        logger.warning(f"Attempt {attempt}/{max_attempts} failed: {str(e)}. Retrying in {sleep_time:.2f}s")
                        time.sleep(sleep_time)
                        
                        # Increase delay for next attempt
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed. Last error: {str(e)}")
            
            # If we get here, all attempts failed
            if last_exception:
                logger.error(f"Operation failed after {max_attempts} attempts")
            return None
            
        return wrapper
    return decorator

def fallback(default_value: Any) -> Callable[[Callable[..., T]], Callable[..., Union[T, Any]]]:
    """
    Fallback decorator that returns a default value if the function fails
    
    Args:
        default_value: Value to return if the function fails
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function failed, using fallback value: {str(e)}")
                return default_value
        return wrapper
    return decorator

def timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    Timeout decorator that limits the execution time of a function
    
    Note: This is a simple implementation that works for most cases,
    but it doesn't handle all edge cases (e.g., non-interruptible I/O).
    For more robust timeout handling, consider using the 'signal' module
    or a library like 'stopit'.
    
    Args:
        seconds: Maximum execution time in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            import signal
            
            def handler(signum, frame):
                raise TimeoutError(f"Function timed out after {seconds} seconds")
                
            # Set the timeout handler
            original_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(int(seconds))
            
            try:
                result = func(*args, **kwargs)
                return result
            except TimeoutError as e:
                logger.error(str(e))
                return None
            finally:
                # Reset the alarm and restore the original handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
                
        return wrapper
    return decorator
