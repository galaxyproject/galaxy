<%inherit file="/base_panels.mako"/>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Tools</div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_tools" src="${h.url_for( 'tool_menu' )}" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%; width: 100%;"> </iframe>
    </div>
</%def>

<%def name="center_panel()">

    ## If a specific tool id was specified, load it in the middle frame
    <%
    if tool_id is not None:
        center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True )
    else:
        center_url = h.url_for( '/static/welcome.html' )
    %>
    
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>

</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a class='panel-header-button' href="${h.url_for( action='history_options' )}" target="galaxy_main"><span>Options</span></a>
            </div>
            <div class="panel-header-text">History</div>
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%;" src="${h.url_for( action='history' )}"></iframe>
    </div>
</%def>