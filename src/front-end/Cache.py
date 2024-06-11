from threading import Lock

class LruCache():
    def __init__(self, cacheSize):
        # Set size of cache
        self.cacheSize = cacheSize

        # Initialize list to store items
        self.cache = []

        # Create a lock
        self.lock = Lock()
    
    def is_full(self):
        # Check if the current size of the cache is equal to the maximum size
        return len(self.cache) == self.cacheSize
    
    """
    Method that attempts to fetch an item from the cache based on its name
    Returns None if the item is not in the cache, or a dictionary if it is in the cache
    """
    def fetch(self, name):
        self.lock.acquire()
        # Get the index of the element to fetch
        index = -1
        for i in range(len(self.cache)):
            curEntry = self.cache[i]
            curName = curEntry["name"]
            if curName == name:
                # If the element is found, set index = i and stop loop
                index = i
                break
        
        # Check if the element was found
        targetElem = None
        if index >= 0:
            # Pop the element to return from the cache
            targetElem = self.cache.pop(index)

            # Append targetElem to the back of the queue
            self.cache.append(targetElem)
        
        self.lock.release()
        # Return target element
        return targetElem

    def evict(self):
        # Items at the head of the list are least recently used
        # So pop at element 0
        retVal = None
        try:
            retVal = self.cache.pop(0)
        except:
            retVal = None

        return retVal
    
    """
    Remove an element from the cache by name
    """
    def invalidate(self, name):
        # Acquire lock
        self.lock.acquire()
        # Get index of the target element to remove
        index = -1
        for i in range(len(self.cache)):
            curElem = self.cache[i]
            if curElem["name"] == name:
                index = i
                break
        
        # Check if the element to invalidate was in the cache
        successFlag = False
        if index >= 0:
            # Remove the element and set the success flag to true
            self.cache.pop(index)
            successFlag = True
        
        # Release lock
        self.lock.release()

        # Return if the invalidation operation was a success
        return successFlag

    """
    Method that attempts to insert objects into the cache
    """
    def insert(self, item):
        self.lock.acquire()
        # Check if the cache is full
        if self.is_full():
            # Evict the least recently used element
            self.evict()

            # Append new item to the end of the cache
            self.cache.append(item)
        else:
            # Append the item to the end of the cache queue
            self.cache.append(item)
        self.lock.release()

