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
    <div class="toolFormTitle">Create Category</div>
    <div class="toolFormBody">
        <form name="create_category_form" id="create_category_form" action="${h.url_for( action='create_category' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <input  name="name" type="textfield" value="${name}" size=40"/>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <input  name="description" type="textfield" value="${description}" size=40"/>
            </div>
            <div class="form-row">
                <input type="submit" name="create_category_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
