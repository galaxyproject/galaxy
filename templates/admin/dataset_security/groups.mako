<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

## Render a row
<%def name="render_row( group_name, group )">
   <td>${group_name}</td>
   <td>${group[2]}</td>
   <td><a href="${h.url_for( controller='admin', action='group_members', group_id=group[0], group_name=group[1] )}">${group[3]}</a></td>
   %if group[4] > 0:
     <td><a href="${h.url_for( controller='admin', action='group_dataset_permitted_actions', group_id=group[0], group_name=group[1] )}">${group[4]}</a></td>
   %else:
     <td>${group[4]}</td>
   %endif
   <td>
     %if len( group[5] ) == 1:
       ${group[5][0]}
     %elif len( group[5] ) > 1:
       %for da in group[5]:
         ${da}<br/>  
       %endfor
     %endif
   </td>
   <td><a href="${h.url_for( controller='admin', action='mark_group_deleted', group_id=group[0] )}">Mark group deleted</a></td>
</%def>

<%def name="title()">Groups</%def>

%if msg:
<div class="donemessage">${msg}</div>
%endif

<h2>Groups</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='create_group' )}">
            Create a new group
        </a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='deleted_groups' )}">
            Manage deleted groups
        </a>
    </li>
</ul>

%if len( groups ) == 0:
    There are no Galaxy groups
%else:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">

      <% 
        render_quick_find = len( groups ) > 50
        ctr = 0
      %>
      %if render_quick_find:
        <%
          anchors = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
          anchor_loc = 0
          anchored = False
          curr_anchor = 'A'
        %>
        <tr>
          <td colspan="6">
            <center>
              |<a href="#A">A</a>|<a href="#B">B</a>|<a href="#C">C</a>|<a href="#D">D</a>|<a href="#E">E</a>|<a href="#F">F</a>
              |<a href="#G">G</a>|<a href="#H">H</a>|<a href="#I">I</a>|<a href="#J">J</a>|<a href="#K">K</a>|<a href="#L">L</a>
              |<a href="#M">M</a>|<a href="#N">N</a>|<a href="#O">O</a>|<a href="#P">P</a>|<a href="#Q">Q</a>|<a href="#R">R</a>
              |<a href="#S">S</a>|<a href="#T">T</a>|<a href="#U">U</a>|<a href="#V">V</a>|<a href="#W">W</a>|<a href="#X">X</a>
              |<a href="#Y">Y</a>|<a href="#Z">Z</a>
            </center>
          </td>
        </tr>
      %endif
      <tr class="header">
        <td>Name</td>
        <td>Priority</td>
        <td>Members</td>
        <td>Datasets</td>
        <td>Group Permitted Actions on Datasets</td>
        <td>&nbsp;</td>
      </tr>
      %for group in groups:
        <% group_name = unescape( group[1], unentities ) %>
        %if render_quick_find and not group_name.upper().startswith( curr_anchor ):
          <% anchored = False %>
        %endif
        <tr>
          %if ctr % 2 == 1:
            <div class="odd_row">
          %endif
          %if render_quick_find and group_name.upper().startswith( curr_anchor ):
            %if not anchored:
              <tr>
                <td colspan="6" class=panel-body">
                  <a name="${curr_anchor}"></a>
                  <div style="float: right;"><a href="#TOP">quick find</a></div>
                  <% anchored = True %>
                </td>
              </tr>
            %endif
            ${render_row( group_name, group )}
          %elif render_quick_find:
            %for anchor in anchors[ anchor_loc: ]:
              %if group_name.upper().startswith( anchor ):
                %if not anchored:
                  <tr>
                    <td colspan="6" class="panel-body">
                      <a name="${anchor}"></a>
                      <div style="float: right;"><a href="#TOP">quick find</a></div>
                      <% 
                        curr_anchor = anchor
                        anchored = True 
                      %>
                    </td>
                  </tr>
                %endif
                ${render_row( group_name, group )}
                <% 
                  anchor_loc = anchors.index( anchor )
                  break 
                %>
              %endif
            %endfor
          %else:
            ${render_row( group_name, group )}
          %endif
          %if ctr % 2 == 1:
            </div>
          %endif
          <% ctr += 1 %>
        </tr>
      %endfor
    %endif
  </table>
</div>
