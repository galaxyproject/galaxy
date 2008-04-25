<%inherit file="/base.mako"/>
<%def name="title()">Your saved histories</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
    jQuery(document).ready( function() {
	// Links with confirmation
	jQuery( "a[@confirm]" ).click( function() {
	    return confirm( jQuery(this).attr( "confirm"  ) )
	})
	
    });
  
    ## FIXME: This depends on javascript, could be moved into controller
    function OnSubmitForm()
    {
      if(document.history_actions.operation[0].checked == true)
      {
	document.history_actions.action = "${h.url_for( action="history_share") }";
      }
      else if(document.history_actions.operation[1].checked == true)
      {
    
	document.history_actions.action = "${h.url_for( action="history_rename") }";
      }
      else if(document.history_actions.operation[2].checked == true)
      {
	if (confirm("Are you sure you want to delete these histories?"))
	{
	    document.history_actions.action = "${h.url_for( action="history_delete" )}";
	}
      }
    
      return true;
    }
</script>
</%def>
  	
%if user.histories:
  <h1>Stored Histories</h1>
  <form name="history_actions" onSubmit="return OnSubmitForm();" method="post" >
      <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
          <tr class="header" align="center"><td></td><td>Name</td><td>Size</td><td>Last modified</td><td>Actions</td></tr>
      %for history in user.histories:
        %if not( history.deleted ):
          <tr>
            <td><input type=checkbox name="id" value="${history.id}"
          %if str(history.id) in ids:
          checked 
          %endif
          ></td><td>${history.name} 
          %if history.deleted:
          (deleted)
          %endif
          </td>
          <td>${len(history.active_datasets)}</td>
          <td>${str(history.update_time)[:19]}</td>
          <td>
            <a href="${h.url_for( action='history_rename', id=history.id )}">rename</a><br />
            <a href="${h.url_for( action='history_switch', id=history.id )}">switch to</a><br />
            <a href="${h.url_for( action='history_delete', id=history.id )}" confirm="Are you sure you want to delete this history?">delete</a>
          </td>
          </tr>
        %endif
      %endfor
   <tr><th colspan="100%">Action</th></tr>
   <tr><td colspan="100%" align="center"><input type="radio" name="operation" value="1" checked>Share <input type="radio" name="operation" value="2">Rename <input type="radio" name="operation" value="3">Delete </td></tr>
   <tr><td colspan="100%" align="center"><input type="submit" name="submit" value="Perform Action"></td></tr>
      </table>
  </form>
%else:
  You have no stored histories
%endif
  