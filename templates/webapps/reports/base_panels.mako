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
    ## Tab area, fills entire width
    <div style="position: absolute; top: 0; left: 0; width: 100%; text-align: center">
        <table class="tab-group" border="0" cellspacing="0" style="margin: auto;">
            <tr>
                <%def name="tab( id, display, href, target='_parent', visible=True, extra_class='' )">
                    <%
                    cls = "tab"
                    if extra_class:
                        cls += " " + extra_class
                    if self.active_view == id:
                        cls += " active"
                    style = ""
                    if not visible:
                        style = "display: none;"
                    %>
                    <td class="${cls}" style="${style}"><a target="${target}" href="${href}">${display}</a></td>
                </%def>
            </tr>
        </table>
    </div>
    ## Logo, layered over tabs to be clickable
    <a class="navbar-brand" href="${h.url_for( app.config.get( 'logo_url', '/' ) )}">
        <img class="navbar-brand-image" src="${h.url_for('/static/favicon.png')}" />
        <span class="navbar-brand-title">Galaxy Reports</span>
        %if app.config.brand:
            <span class='brand'>/ ${app.config.brand}</span>
        %endif
    </a>
</%def>
