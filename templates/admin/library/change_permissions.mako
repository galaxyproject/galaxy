<%inherit file="/base.mako"/>
<%def name="title()">Change Dataset Permissions</%def>

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
  <div class="toolFormTitle">Change Dataset Access Permissions</div>
  <div class="toolFormBody">
      <form name="change_permission_form" action="${h.url_for( action='change_permissions' )}" method="post">
          <input type="hidden" name="ids" value="${",".join( [ str(d.id) for d in datasets ] )}">
          <div class="form-row">
              <% groups = trans.app.model.Group.select() %>
              <% active_group_ids = [ assoc.group.id for assoc in datasets[0].dataset.groups ] %>
              <div class="toolParamHelp" style="clear: both;">
                Check each group which should have access to this dataset.
              </div>
              %for group in groups:
                %if group.id in active_group_ids:
                  <% assoc = filter( lambda x: x.group_id == group.id, datasets[0].dataset.groups )[0] %>
                %else:
                  <% assoc = None %>
                %endif
                <input type="checkbox" name="group_${group.id}" class="groupCheckbox"
                %if assoc is not None:
                  checked
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
              <input type="submit" name="change_permissions" value="Save">
          </div>
      </form>
  </div>
  </div>
