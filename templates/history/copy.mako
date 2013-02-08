<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Copy History</%def>

<div class="toolForm">
  <div class="toolFormTitle">Copy History</div>
    <div class="toolFormBody">
        <form action="${h.url_for( controller='history', action='copy' )}" method="post" >
            <div class="form-row">
                %if id_argument is not None:
                  <input type="hidden" name="id" value="${id_argument}">
                %endif
                You can make a copy of the history that includes all datasets in the original history or just the active 
                (not deleted) datasets.
            </div>
            <div class="form-row">
                <input type="radio" name="copy_choice" value="activatable"> Copy all datasets, including deleted ones
            </div>
            <div class="form-row">
                <input type="radio" name="copy_choice" value="active"> Copy only active (not deleted) datasets
            </div>
            <div class="form-row">
                <input type="submit" name="copy_choice_button" value="Copy">
            </div>
        </form>
    </div>
</div>
