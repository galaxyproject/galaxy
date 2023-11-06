<%inherit file="/base/base_panels.mako"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "reports" )}
</%def>

<%def name="init()">
    ${parent.init()}
    <%
        self.body_class = "reports"
    %>
</%def>

## Default title
<%def name="title()">Reports</%def>

## Masthead
<%def name="masthead()">
    <nav id="masthead" class="masthead-simple navbar navbar-expand navbar-fixed-top justify-content-center navbar-dark">
        <a href="${h.url_for( app.config.get( 'logo_url', '/' ) )}" aria-label="homepage" class="navbar-brand">
            <img alt="logo" class="navbar-brand-image" src="${h.url_for('/static/favicon.svg')}">
            <span class="navbar-brand-title">
                Reports
                %if app.config.brand:
                    / ${app.config.brand}
                %endif
            </span>
        </a>
         <ul class="navbar-nav"/>
    </nav>
</%def>
