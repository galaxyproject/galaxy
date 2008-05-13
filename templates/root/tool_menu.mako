<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>Galaxy Tools</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link href="${h.url_for('/static/style/tool_menu.css')}" rel="stylesheet" type="text/css" />

<script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>

<script type="text/javascript">
    var q = jQuery.noConflict();
    q(document).ready(function() { 
        q( "div.toolSectionBody" ).hide();
        q( "div.toolSectionTitle > span" ).wrap( "<a href='#'></a>" )
        var last_expanded = null;
        q( "div.toolSectionTitle" ).each( function() { 
           var body = q(this).next( "div.toolSectionBody" );
           q(this).click( function() {
               if ( body.is( ":hidden" ) ) {
                   if ( last_expanded ) last_expanded.slideUp( "fast" );
                   last_expanded = body;
                   body.slideDown( "fast" );
               }
               else {
                   body.slideUp( "fast" );
                   last_expanded = null;
               }
               return false;
           });
        });
        q( "a[@minsizehint]" ).click( function() {
            if ( parent.handle_minwidth_hint ) {
                parent.handle_minwidth_hint( q(this).attr( "minsizehint" ) );
            }
        });
    });
</script>

</head>

<body class="toolMenuPage">

<div class="toolMenu">

<div class="toolSectionList">
%for i, section in enumerate( toolbox.sections ):
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
              <%
              if tool.input_required:
                  link = h.url_for( 'tool_runner', tool_id=tool.id )
              else:
                  link = h.url_for( tool.action, ** tool.get_static_param_values( t ) )
              %>
              ## FIXME: This doesn't look right
              ## %if "[[" in tool.description and "]]" in tool.description:
              ##   ${tool.description.replace( '[[', '<a href="link" target="galaxy_main">' % $tool.id ).replace( "]]", "</a>" )
              %if tool.name:
                <a id="link-${tool.id}" href="${link}" target="galaxy_main" minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${tool.name}</a> ${tool.description} 
              %else:
                <a id="link-${tool.id}" href="${link}" target="galaxy_main" minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${tool.description}</a>
              %endif
            </div>
            %endif
        %endfor
      </div>
   </div>
%endfor

## Link to workflow management. The location of this may change, but eventually
## at least some workflows will appear here (the user should be able to
## configure which of their stored workflows appear in the tools menu). 

%if app.config.enable_beta_features:
    <div class="toolSectionPad"></div>
    <div class="toolSectionPad"></div>
    <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
      <span>Workflow <i>(beta)</i></span>
    </div>
    <div id="XXinternalXXworkflow" class="toolSectionBody">
      <div class="toolSectionBg">
            <div class="toolTitle">
                <a href="${h.url_for( controller='workflow', action='index' )}" target="galaxy_main">Manage</a> workflows
            </div>
      </div>
    </div>
%endif

</div>

</div>

<div style="height: 20px"></div>

</body>

</html>