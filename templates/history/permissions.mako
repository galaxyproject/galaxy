<%inherit file="/base.mako"/>
<%def name="title()">Change Default History Permitted Actions</%def>

%if trans.user:
  <script type="text/javascript">
    var q = jQuery.noConflict();
    q( document ).ready( function () {
        // initialize state
        q("input.groupCheckbox").each( function() {
            if ( ! q(this).is(":checked") ) q("div#" + this.name).hide();
        });
        // handle events
        q("input.groupCheckbox").click( function() {
            if ( q(this).is(":checked") ) {
                q("div#" + this.name).slideDown("fast");
            } else {
                q("div#" + this.name).slideUp("fast");
            }
        });
    });
  </script>
  <div class="toolForm">
  <div class="toolFormTitle">Change Default History Permitted Actions</div>
  <div class="toolFormBody">
      <form name="set_permitted_actions" method="post">
          <div class="form-row">
                <% user_groups = [ assoc.group for assoc in trans.user.groups ] %>
                <% cur_groups = [ assoc.group for assoc in trans.get_history().default_groups ] %>
                %for group in user_groups:
                    <input type="checkbox" name="group_${group.id}" class="groupCheckbox"
                    %if group in cur_groups:
                      <% assoc = filter( lambda x: x.group_id == group.id, trans.get_history().default_groups )[0] %>
                      checked
                    %else:
                      <% assoc = None %>
                    %endif
                    /> ${group.name} <br/>
                    <div class="permissionContainer" id="group_${group.id}">
                    %for k, v in trans.app.security_agent.permitted_actions.items():
                        <input type="checkbox" name="group_${group.id}_${k}"
                        %if assoc is not None and v in assoc.permitted_actions:
                          checked
                        %endif
                        /> ${trans.app.security_agent.get_permitted_action_description(k)} <br/>
                    %endfor
                    </div>
                %endfor
            
            <div style="clear: both"></div>
            
            <div class="toolParamHelp" style="clear: both;">
                This will change the default permitted actions assigned
                to new datasets in your current history.  You may also
                specify the defaults for new histories via the
                <a href="${h.url_for(controller='user')}">user options</a>.

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
