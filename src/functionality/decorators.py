import time
from functools import wraps


def timing(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        t_start = time.perf_counter()
        result = func(*args, **kwargs)
        t_end = time.perf_counter()
        t = t_end - t_start
        print(f"The function {func.__name__} completed in {t:.6f} sec")
        return result
    return wrapper


def cache_result(func):
    """Decorator to cache function results based on arguments."""
    cache = {}

    @wraps(func)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        cache[args] = result
        return result

    return wrapper