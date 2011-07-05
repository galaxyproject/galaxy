<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Clone History</%def>

<div class="toolForm">
  <div class="toolFormTitle">Clone History</div>
    <div class="toolFormBody">
        <form action="${h.url_for( controller='history', action='clone' )}" method="post" >
            <div class="form-row">
                %if id_argument is not None:
                  <input type="hidden" name="id" value="${id_argument}">
                %endif
                You can clone the history such that the clone will include all items in the original
                history, or you can eliminate the original history's deleted items from the clone.
            </div>
            <div class="form-row">
                <input type="radio" name="clone_choice" value="activatable"> Clone all history items, including deleted items
            </div>
            <div class="form-row">
                <input type="radio" name="clone_choice" value="active"> Clone only items that are not deleted
            </div>
            <div class="form-row">
                <input type="submit" name="clone_choice_button" value="Clone">
            </div>
        </form>
    </div>
</div>
