<%inherit file="/export_base.mako"/>

<%namespace file="/display_common.mako" import="*" />

<%def name="init()">
<%
    parent.init()
    self.active_view="workflow"
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        .toolForm {
            max-width: 350px;
        }
    </style>
</%def>

<%def name="render_export_to_myexp(item)">
    ##
    ## Renders form for exporting workflow to myExperiment.
    ##
    <h3>Export to myExperiment</h3>
    
    <div class="toolForm"> 
        <form action="${h.url_for(controller='workflow', action='export_to_myexp', id=trans.security.encode_id( item.id ) )}" 
                method="POST">
            <div class="form-row"> 
                <label>myExperiment username:</label> 
                <input type="text" name="myexp_username" value="" size="40"/> 
            </div> 
            <div class="form-row"> 
                <label>myExperiment password:</label> 
                <input type="password" name="myexp_password" value="" size="40"/> 
            </div> 
            <div class="form-row"> 
                <input type="submit" value="Export"/> 
            </div> 
        </form> 
    </div>    
</%def>

<%def name="render_more(item)">
    ## Add form to export to myExperiment.
    ${self.render_export_to_myexp(item)}

    ## Add link to render as SVG image.
    <h3>Create Image</h3>
    
    <a href="${h.url_for(controller='workflow', action='gen_image', id=trans.security.encode_id( item.id ) )}">
        Create image of ${get_class_display_name( item.__class__ ).lower()} in SVG format
    </a>
</%def>

<%def name="center_panel()">
    ${parent.body()}
</%def>
