<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select a category</div>
    <div class="toolFormBody">
        <form id="select_category" name="select_category" action="${h.url_for( controller='common', action='add_category', cntrller=cntrller, id=id, use_panels=use_panels )}" method="post" >
            <div class="form-row">
                <label>Category:</label>
                ${category_select_list.get_html()}
            </div>
            <div class="toolParamHelp" style="clear: both;">
                Multi-select list - hold the appropriate key while clicking to select multiple columns
            </div>
            <div class="form-row">
                <input type="submit" name="add_category_button" value="Add tool to categories"/>
            </div>
        </form>
    </div>
</div>
