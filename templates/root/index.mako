<%inherit file="/base_panels.mako"/>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Tools</div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_tools" src="${h.url_for( 'tool_menu' )}" width="100%" height="100%" frameborder="0" style="margin: 0; border: 0 none; height: 100%;"> </iframe>
    </div>
</%def>

<%def name="center_panel()">
    <table class="column-layout" cellpadding="0" cellspacing="0" border="0" height="100%" width="100%">
        <tr height="100%" style="height: 100%">
            <td height="100%" style="height: 100%;">
                ## If a specific tool id was specified, load it in the middle frame
                %if tool_id is not None:
                    <iframe name="galaxy_main" id="galaxy_main" width="100%" height="100%" frameborder="0" style="margin: 0; border: 0 none; width: 100%; height: 100%;" src="${h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True )}"> </iframe>
                %else:
                    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="margin: 0; border: 0 none; position: static; width: 100%; height: 100%;" src="${h.url_for( '/static/welcome.html' )}"> </iframe>
                %endif
            </td>
        </tr>
    </table>
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>History (<a href="${h.url_for( action='history_options' )}" target="galaxy_main">options</a>)</div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="margin: 0; border: 0 none; height: 100%;" src="${h.url_for( action='history' )}"></iframe>
    </div>
</%def>