/*
MIT LICENSE
Copyright (c) 2007 Monsur Hossain (http://www.monsur.com)

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
*/

// ****************************************************************************
// CachePriority ENUM
// An easier way to refer to the priority of a cache item
var CachePriority = {
    Low: 1,
    Normal: 2,
    High: 4
}

// ****************************************************************************
// Cache constructor
// Creates a new cache object
// INPUT: maxSize (optional) - indicates how many items the cache can hold.
//                             default is -1, which means no limit on the 
//                             number of items.
function Cache(maxSize) {
    this.items = {};
    this.count = 0;
    if (maxSize == null)
        maxSize = -1;
    this.maxSize = maxSize;
    this.fillFactor = .75;
    this.purgeSize = Math.round(this.maxSize * this.fillFactor);
    
    this.stats = {}
    this.stats.hits = 0;
    this.stats.misses = 0;
}

// ****************************************************************************
// Cache.getItem
// retrieves an item from the cache, returns null if the item doesn't exist
// or it is expired.
// INPUT: key - the key to load from the cache
Cache.prototype.getItem = function(key) {

    // retrieve the item from the cache
    var item = this.items[key];
    
    if (item != null) {
        if (!this._isExpired(item)) {
            // if the item is not expired
            // update its last accessed date
            item.lastAccessed = new Date().getTime();
        } else {
            // if the item is expired, remove it from the cache
            this._removeItem(key);
            item = null;
        }
    }
    
    // return the item value (if it exists), or null
    var returnVal = null;
    if (item != null) {
        returnVal = item.value;
        this.stats.hits++;
    } else {
        this.stats.misses++;
    }
    return returnVal;
}

// ****************************************************************************
// Cache.setItem
// sets an item in the cache
// parameters: key - the key to refer to the object
//             value - the object to cache
//             options - an optional parameter described below
// the last parameter accepts an object which controls various caching options:
//      expirationAbsolute: the datetime when the item should expire
//      expirationSliding: an integer representing the seconds since
//                         the last cache access after which the item
//                         should expire
//      priority: How important it is to leave this item in the cache.
//                You can use the values CachePriority.Low, .Normal, or 
//                .High, or you can just use an integer.  Note that 
//                placing a priority on an item does not guarantee 
//                it will remain in cache.  It can still be purged if 
//                an expiration is hit, or if the cache is full.
//      callback: A function that gets called when the item is purged
//                from cache.  The key and value of the removed item
//                are passed as parameters to the callback function.
Cache.prototype.setItem = function(key, value, options) {

    function CacheItem(k, v, o) {
        if ((k == null) || (k == ''))
            throw new Error("key cannot be null or empty");
        this.key = k;
        this.value = v;
        if (o == null)
            o = {};
        if (o.expirationAbsolute != null)
            o.expirationAbsolute = o.expirationAbsolute.getTime();
        if (o.priority == null)
            o.priority = CachePriority.Normal;
        this.options = o;
        this.lastAccessed = new Date().getTime();
    }

    // add a new cache item to the cache
    if (this.items[key] != null)
        this._removeItem(key);
    this._addItem(new CacheItem(key, value, options));
    
    // if the cache is full, purge it
    if ((this.maxSize > 0) && (this.count > this.maxSize)) {
        this._purge();
    }
}

// ****************************************************************************
// Cache.clear
// Remove all items from the cache
Cache.prototype.clear = function() {

    // loop through each item in the cache and remove it
    for (var key in this.items) {
      this._removeItem(key);
    }  
}

// ****************************************************************************
// Cache._purge (PRIVATE FUNCTION)
// remove old elements from the cache
Cache.prototype._purge = function() {
    
    var tmparray = new Array();
    
    // loop through the cache, expire items that should be expired
    // otherwise, add the item to an array
    for (var key in this.items) {
        var item = this.items[key];
        if (this._isExpired(item)) {
            this._removeItem(key);
        } else {
            tmparray.push(item);
        }
    }
    
    if (tmparray.length > this.purgeSize) {

        // sort this array based on cache priority and the last accessed date
        tmparray = tmparray.sort(function(a, b) { 
            if (a.options.priority != b.options.priority) {
                return b.options.priority - a.options.priority;
            } else {
                return b.lastAccessed - a.lastAccessed;
            }
        });
        
        // remove items from the end of the array
        while (tmparray.length > this.purgeSize) {
            var ritem = tmparray.pop();
            this._removeItem(ritem.key);
        }
    }
}

// ****************************************************************************
// Cache._addItem (PRIVATE FUNCTION)
// add an item to the cache
Cache.prototype._addItem = function(item) {
    this.items[item.key] = item;
    this.count++;
}

// ****************************************************************************
// Cache._removeItem (PRIVATE FUNCTION)
// Remove an item from the cache, call the callback function (if necessary)
Cache.prototype._removeItem = function(key) {
    var item = this.items[key];
    delete this.items[key];
    this.count--;
    
    // if there is a callback function, call it at the end of execution
    if (item.options.callback != null) {
        var callback = function() {
            item.options.callback(item.key, item.value);
        }
        setTimeout(callback, 0);
    }
}

// ****************************************************************************
// Cache._isExpired (PRIVATE FUNCTION)
// Returns true if the item should be expired based on its expiration options
Cache.prototype._isExpired = function(item) {
    var now = new Date().getTime();
    var expired = false;
    if ((item.options.expirationAbsolute) && (item.options.expirationAbsolute < now)) {
        // if the absolute expiration has passed, expire the item
        expired = true;
    } 
    if ((expired == false) && (item.options.expirationSliding)) {
        // if the sliding expiration has passed, expire the item
        var lastAccess = item.lastAccessed + (item.options.expirationSliding * 1000);
        if (lastAccess < now) {
            expired = true;
        }
    }
    return expired;
}

Cache.prototype.toHtmlString = function() {
    var returnStr = this.count + " item(s) in cache<br /><ul>";
    for (var key in this.items) {
        var item = this.items[key];
        returnStr = returnStr + "<li>" + item.key.toString() + " = " + item.value.toString() + "</li>";
    }
    returnStr = returnStr + "</ul>";
    return returnStr;
}
