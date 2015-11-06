define([ 'jquery' ], function( jQuery ){
'use_strict';
var $ = jQuery;
// ============================================================================

// Create GalaxyAsync object.
var GalaxyAsync = function(log_action) {
    this.url_dict = {};
    this.log_action = (log_action === undefined ? false : log_action);
};

GalaxyAsync.prototype.set_func_url = function( func_name, url ) {
    this.url_dict[func_name] = url;
};

// Set user preference asynchronously.
GalaxyAsync.prototype.set_user_pref = function( pref_name, pref_value ) {
    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({
        url: url,
        data: { "pref_name" : pref_name, "pref_value" : pref_value },
        error: function() { return false; },
        success: function() { return true; }
    });
};

// Log user action asynchronously.
GalaxyAsync.prototype.log_user_action = function( action, context, params ) {
    if (!this.log_action) { return; }

    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({
        url: url,
        data: { "action" : action, "context" : context, "params" : params },
        error: function() { return false; },
        success: function() { return true; }
    });
};

// ============================================================================
    return GalaxyAsync;
});
