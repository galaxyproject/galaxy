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
    <div class="toolFormTitle">Create Repository</div>
    <div class="toolFormBody">
        <form name="create_repository_form" id="create_repository_form" action="${h.url_for( controller='repository', action='create_repository' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <input  name="name" type="textfield" value="${name}" size="40"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Synopsis:</label>
                <input  name="description" type="textfield" value="${description}" size="80"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Detailed description:</label>
                %if long_description:
                    <pre><textarea name="long_description" rows="3" cols="80">${long_description}</textarea></pre>
                %else:
                    <textarea name="long_description" rows="3" cols="80"></textarea>
                %endif
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Categories</label>
                <div class="form-row">
                    <select name="category_id" multiple>
                        %for category in categories:
                            %if category.id in selected_categories:
                                <option value="${trans.security.encode_id( category.id )}" selected>${category.name}</option>
                            %else:
                                <option value="${trans.security.encode_id( category.id )}">${category.name}</option>
                            %endif
                        %endfor
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Multi-select list - hold the appropriate key while clicking to select multiple categories.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="create_repository_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
