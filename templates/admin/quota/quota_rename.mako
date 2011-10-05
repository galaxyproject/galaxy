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
    <div class="toolFormTitle">Change quota name and description</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='admin', action='rename_quota' )}" method="post" >
            <div class="form-row">
                <input  name="webapp" type="hidden" value="${webapp}" size=40"/>
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input  name="description" type="textfield" value="${description}" size=40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="rename" value="submitted"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="id" value="${id}"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="rename_quota_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
