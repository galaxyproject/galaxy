<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<%def name="title()">Users</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>
  </div>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td>&nbsp;</td>
    %if len( users ) == 0:
      <tr><td>There are no Galaxy users</td></tr>
    %else:
      <% 
        render_quick_find = len( users ) > 50
        ctr = 0
      %>
      %if render_quick_find:
        <%
          anchors = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
          anchor_loc = 0
          anchored = False
          curr_anchor = 'A'
        %>
        <tr class="header"><td><center><a name="TOP">Galaxy Users - Quick Find</a></td></center></tr>
        <tr>
          <td>
            |<a href="#A">A</a>|<a href="#B">B</a>|<a href="#C">C</a>|<a href="#D">D</a>|<a href="#E">E</a>|<a href="#F">F</a>
            |<a href="#G">G</a>|<a href="#H">H</a>|<a href="#I">I</a>|<a href="#J">J</a>|<a href="#K">K</a>|<a href="#L">L</a>
            |<a href="#M">M</a>|<a href="#N">N</a>|<a href="#O">O</a>|<a href="#P">P</a>|<a href="#Q">Q</a>|<a href="#R">R</a>
            |<a href="#S">S</a>|<a href="#T">T</a>|<a href="#U">U</a>|<a href="#V">V</a>|<a href="#W">W</a>|<a href="#X">X</a>
            |<a href="#Y">Y</a>|<a href="#Z">Z</a>
          </td>
        </tr>
      %else:
        <tr class="header"><td><center>Galaxy Users</td></center></tr>
      %endif
      %for user in users:
        <% email = unescape( user[1], unentities ) %>
        %if render_quick_find and not email.upper().startswith( curr_anchor ):
          <% anchored = False %>
        %endif
        <tr>
          %if ctr % 2 == 1:
            <div class="odd_row">
          %endif
          <td>  
            %if render_quick_find and email.upper().startswith( curr_anchor ):
              %if not anchored:
                <a name="${curr_anchor}"></a>
                <hr/>
                <div style="float: right;"><a href="#TOP">quick find</a></div>
                <br/>
                <% anchored = True %>
              %endif
              <a href="${h.url_for( controller='admin', action='specified_users_groups', user_id=user[0], user_email=user[1] )}">${email}</a>
            %elif render_quick_find:
              %for anchor in anchors[ anchor_loc: ]:
                %if email.upper().startswith( anchor ):
                  %if not anchored:
                    <a name="${anchor}"></a>
                    <hr/>
                    <div style="float: right;"><a href="#TOP">quick find</a></div>
                    <br/>
                    <% 
                      curr_anchor = anchor
                      anchored = True 
                    %>
                  %endif
                  <a href="${h.url_for( controller='admin', action='specified_users_groups', user_id=user[0], user_email=user[1] )}">${email}</a>
                  <% 
                    anchor_loc = anchors.index( anchor )
                    break 
                  %>
                %endif
              %endfor
            %else:
              <a href="${h.url_for( controller='admin', action='specified_users_groups', user_id=user[0], user_email=user[1] )}">${email}</a>
            %endif
          </td>
          %if ctr % 2 == 1:
            </div>
          %endif
          <% ctr += 1 %>
        </tr>
      %endfor
    %endif
  </table>
</div>
