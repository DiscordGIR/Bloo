from collections import OrderedDict
from functools import wraps

def async_cacher(size=1024):
    """Caches the result of a function
    
    Parameters
    ----------
    size : int, optional
        "Size (in bytes)"
    
    """
    cache = OrderedDict()

    def decorator(fn):
        @wraps(fn)
        async def memoizer(*args, **kwargs):
            key = str((args, kwargs))
            try:
                cache[key] = cache.pop(key)
            except KeyError:
                if len(cache) >= size:
                    cache.popitem(last=False)
                cache[key] = await fn(*args, **kwargs)
            return cache[key]
        return memoizer
    return decorator
