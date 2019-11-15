<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(function(){
            $("input:text:first").focus();
        })
    </script>
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create Component</div>
    <div class="toolFormBody">
        <form name="create_component" id="create_component" action="${h.url_for( controller='repository_review', action='create_component' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <input name="name" type="textfield" value="${name | h}" size=40"/>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <input name="description" type="textfield" value="${description | h}" size=40"/>
            </div>
            <div class="form-row">
                <input type="submit" name="create_component_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
