/* 
    JSONCookie: Uses JSON to allow the settings of multiple preferences in one cookie.
    Kanwei Li, 2009
    
    cookie = new JSONCookie("cookie_name"); // Pass in the name of the cookie
    
    // Gets the value of a preference, returns optional second argument if pref not found
    cookie.get("pref", "val_if_not_found"); 
    
    cookie.set("pref", "val"); // Sets a value for the preference and saves cookie
    cookie.unset("pref"); // Unsets the preference and saves cookie
    cookie.clear() // Deletes the cookie

*/

function JSONCookie(name) {
    this.cookie_name = name;
    
}

JSONCookie.prototype = {
    json_data : function() {
        cookie = $.cookie(this.cookie_name);
        return cookie ? JSON.parse(cookie) : null;
    },
    
    save : function(data) {
        $.cookie(this.cookie_name, JSON.stringify(data));
    },
    
    get : function(attr, else_val) {
        data = this.json_data();
        if (data && data[attr]) {   return data[attr];            
        } else if (else_val) {      return else_val;
        } else {                    return null;
        }
    },
    
    set : function(attr, val) {
        data = this.json_data();
        if (data) {
            data[attr] = val;
        } else {
            data = { attr : val }
        }
        this.save(data);
    },
    
    unset : function(attr) {
        data = this.json_data();
        if (data) {
            delete data[attr];
        }
        this.save(data);
    },
    
    clear : function() {
        this.save(null);
    }
    
};