<%inherit file="/base.mako"/>
<%def name="title()">Change Default History Permitted Actions</%def>

%if trans.user:
  <div class="toolForm">
  <div class="toolFormTitle">Change Default History Permitted Actions</div>
  <div class="toolFormBody">
      <form name="set_permitted_actions" method="post">
          <div class="form-row">
                <% user_groups = [ assoc.group for assoc in trans.user.groups ] %>
                <% cur_groups = [ assoc.group for assoc in trans.get_history().default_groups ] %>
            <div style="float: left; width: 250px; margin-right: 10px;">
                <table>
                <tr><th>Group</th><th>In</th><th>Out</th></tr>
                %for group in user_groups:
                <tr><td>${group.name}</td><td><input type="radio" name="group_${group.id}" value="in"
                %if group in cur_groups:
                checked
                %endif
                ></td><td><input type="radio" name="group_${group.id}" value="out"
                %if group not in cur_groups:
                checked
                %endif
                ></td></tr>
                %endfor
                </table>
            </div>
            
            <div style="clear: both"></div>
            
            <div class="toolParamHelp" style="clear: both;">
                This will change the default permitted actions assigned to new datasets for your current history.
            </div>
            <div style="clear: both"></div>
          </div>
          <div class="form-row">
              <input type="submit" name="set_permitted_actions" value="Save">
          </div>
      </form>
  </div>
  </div>
%endif