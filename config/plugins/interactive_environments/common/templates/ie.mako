<%def name="default_javascript_variables()">
// Globals

// Following three are for older-style IE proxies, newer dynamic Galaxy proxy
// does not use these.
ie_password_auth = ${ ie_request.javascript_boolean(ie_request.attr.PASSWORD_AUTH) };
ie_password = '${ ie_request.notebook_pw }';


var galaxy_root = '${ ie_request.attr.root }';
var app_root = '${ ie_request.attr.app_root }';
var ie_readiness_url = '${ h.url_for("/interactive_environments/ready") }';
</%def>


<%def name="load_default_js()">
${h.css( 'base' ) }
${h.js( 'libs/jquery/jquery',
        'libs/toastr',
        'libs/require')}
</%def>

<%def name="plugin_require_config()">
require.config({
    baseUrl: app_root,
    paths: {
        "plugin" : app_root + "js",
        "galaxy.interactive_environments": "${h.url_for('/static/scripts/galaxy.interactive_environments')}",
    },
    urlArgs: "v=${app.server_starttime}",
});

window.onbeforeunload = function() {
    return 'You are leaving your Interactive Environment.';
};

</%def>
