<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>

<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

<script type='text/javascript' src="/static/scripts/jquery.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.dimensions.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.ui.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.blockUI.js"> </script>
<script type='text/javascript' src="/static/scripts/jt.panels.js"> </script>
<script>

$( function() {
    $.blockUI( "<b><img style='vertical-align: middle;' src='${h.url_for( '/static/style/data_running.gif' )}'/> Loading Galaxy Workflow Editor...</b>", 
               { border: "solid #AAAA66 1px", background: "#FFFFCC", padding: "20px", width: "auto" } );
               
    make_left_panel( $("#tool-area"), $("#canvas-area"), $("#left-border" ) );
    // Insert div that covers everything when dragging the borders
    $("<div id='DD-helper' style='background: white; top: 0; left: 0; width: 100%; height: 100%; position: absolute; z-index: 9000;'></div>")
        .css("opacity", "0.01").appendTo("body").hide(); 
    // Show border visual cues
    $( "#left-border-inner" ).show();   
})

function notify() {
    $.unblockUI();
}

</script>

<style>
body, html
{
    overflow: hidden;
    margin: 0;
    padding: 0;
    width: 100%;
	height: 100%;
	background: #eee;
}
#tool-area {
    background: url(${h.url_for('/static/style/menu_bg.png')});
    ## border-top: solid #999 1px;
    position: absolute;
    top: 0px; left: 0; bottom: 0;
    width: 300px;
    overflow: scroll;
}
div.toolMenu {
    margin: 5px;
}
div.toolSectionPad {
    margin: 0;
    padding: 0;
    height: 5px;
    font-size: 0px;
}
div.toolSectionDetailsInner { 
  margin-left: 5px;
  margin-right: 5px;
}
div.toolSectionTitle {
  padding-bottom: 0px;
  font-weight: bold;
}
div.toolTitle {
  padding-top: 5px;
  padding-bottom: 5px;
  margin-left: 16px;
  margin-right: 10px;
  display: list-item;
  list-style: square outside;
}
div.toolFormRow {
  position: relative;
}

#canvas-area {
    ## border-top: solid #999 1px;
    position: absolute;
    top: 0; left: 305px; bottom: 0; right: 0;
    overflow: none;
}
#left-border
{
    position: absolute;
    top: 0; left: 300px; bottom: 0; right: 0;
    background: #eeeeee;
    border-left: solid #999 1px;
    border-right: solid #999 1px;
    padding-right: 1px;
    padding-left: 1px;
    width: 5px;
    z-index: 10000;
}
</style>

<script>
function add_node_for_tool( id ) {
   window.frames.canvas.add_node_for_tool( id );
}
</script>

</head>
    <body scroll="no">
        ## <div id="masthead">
        ##      <iframe name="galaxy_masthead" src="${h.url_for( controller='root', action='masthead' )}" width="38" height="100%" frameborder="0" scroll="no" style="margin: 0; border: 0 none; width: 100%; height: 38px; overflow: hidden;"> </iframe>
        ## </div>
        <div id="tool-area">
            <div class="toolMenu">
            <div class="toolSectionList">
            %for i, section in enumerate( app.toolbox.sections ):
               %if i > 0:
                  <div class="toolSectionPad"></div> 
               %endif
               <div class="toolSectionTitle" id="title_${section.id}">
                  <span>${section.name}</span>
               </div>
               <div id="${section.id}" class="toolSectionBody">
                  <div class="toolSectionBg">
                     %for tool in section.tools:
                        %if not tool.hidden:
                        <div class="toolTitle">
                          ## #if $tool.input_required
                          ##    #set $link = $h.url_for( 'tool_runner', tool_id=$tool.id )
                          ## #else
                          ##    #set $link = $h.url_for( $tool.action, ** $tool.get_static_param_values( $t ) )
                          ## #end if
                          %if "[[" in tool.description and "]]" in tool.description:
                            ${tool.description.replace( '[[', '<a href="javascript:add_node_for_tool( ${tool.id} )">' % tool.id ).replace( "]]", "</a>" )}
                          %elif tool.name:
                            <a id="link-${tool.id}" href="javascript:add_node_for_tool( '${tool.id}' )">${tool.name}</a> ${tool.description}
                          %else:
                            <a id="link-${tool.id}" href="javascript:add_node_for_tool( '${tool.id}' )">${tool.description}</a>
                          %endif
                        </div>
                        %endif
                     %endfor
                  </div>
               </div>
            %endfor
            </div>
            </div>
        </div>
        <div id="left-border"><div id="left-border-inner" style="display: none;"></div></div>
        <div id="canvas-area">
            <iframe name="canvas" width="100%" height="100%" frameborder="0" src="${h.url_for( action='canvas' )}">
        </div>
                        
    </body>
</html>