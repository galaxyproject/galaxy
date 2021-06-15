<%def name="load_default_js()">
${h.css( 'base' ) }
${h.dist_js('libs.chunk',
            'base.chunk',
            'generic.bundled')}
</%def>

<%def name="default_javascript_variables()">
// Globals

// Following three are for older-style IE proxies, newer dynamic Galaxy proxy
// does not use these.
ie_password_auth = ${ ie_request.javascript_boolean(ie_request.attr.PASSWORD_AUTH) };
ie_password = '${ ie_request.notebook_pw }';


var galaxy_root = '${ ie_request.attr.root }';
var app_root = '${ ie_request.attr.app_root }';
var ie_readiness_url = '${ h.url_for("/interactive_environments/ready") }';

window.IES = bundleEntries.IES;
window.toastr = bundleEntries.Toast;

window.onbeforeunload = function() {
    return 'You are leaving your Interactive Environment.';
};
</%def>

<%def name="load_default_app()">
<script src="${'%sjs/main.js?v=%s' % (ie_request.attr.app_root, app.server_starttime)}" type="text/javascript"></script>
</%def>
