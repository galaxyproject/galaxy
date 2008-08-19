<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<%def name="title()">Manage Group Membership</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <% gn = unescape( group_name, unentities ) %>
    <tr><td>&nbsp;</td></tr>
    <tr>
      <td>
        <table border="0">
          <form name="group_create" action="${h.url_for( controller='admin', action='update_group_members', group_id=group_id, group_name=group_name )}" method="post" >
            %if len( users ) == 0:
              <tr><td>There are no Galaxy users</td></tr>
            %else:
              <tr class="header"><td>Members of '${gn}' - Quick Find</td></tr>
              <tr>
                <td>
                  |<a href="#A">A</a>|<a href="#B">B</a>|<a href="#C">C</a>|<a href="#D">D</a>|<a href="#E">E</a>|<a href="#F">F</a>
                  |<a href="#G">G</a>|<a href="#H">H</a>|<a href="#I">I</a>|<a href="#J">J</a>|<a href="#K">K</a>|<a href="#L">L</a>
                  |<a href="#M">M</a>|<a href="#N">N</a>|<a href="#O">O</a>|<a href="#P">P</a>|<a href="#Q">Q</a>|<a href="#R">R</a>
                  |<a href="#S">S</a>|<a href="#T">T</a>|<a href="#U">U</a>|<a href="#V">V</a>|<a href="#W">W</a>|<a href="#X">X</a>
                  |<a href="#Y">Y</a>|<a href="#Z">Z</a>
                </td>
              </tr>
              <tr>
                <td>
                  <%
                    ctr = 0
                    anchors = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
                    anchor_loc = 0
                    anchored = False
                    curr_anchor = 'A'
                  %>
                  %for user in users:
                    <% 
                      email = unescape( user[1], unentities )
                      check = False 
                    %>
                    %for member in members:
                      <% member_email = unescape( member[1], unentities ) %>
                      %if email == member_email:
                        <% 
                          check = True
                          break
                        %>
                      %endif
                    %endfor
                    %if not email.upper().startswith( curr_anchor ):
                      <% anchored = False %>
                    %endif
                    %if ctr % 2 == 1:
                      <tr class="odd_row">
                    %else:
                      <tr class="tr">
                    %endif
                    <td>  
                      %if email.upper().startswith( curr_anchor ):
                        %if not anchored:
                          <a name="${curr_anchor}"><hr/></a><br/>
                          <% anchored = True %>
                        %endif
                        %if check:
                          <input type="checkbox" name="members" value="${user[0]}" checked/> ${email}
                        %else:
                          <input type="checkbox" name="members" value="${user[0]}"/> ${email}
                        %endif
                      %else:
                        %for anchor in anchors[ anchor_loc: ]:
                          %if email.upper().startswith( anchor ):
                            %if not anchored:
                              <a name="${anchor}"><hr/></a><br/>
                              <% 
                                curr_anchor = anchor
                                anchored = True 
                              %>
                            %endif
                            %if check:
                              <input type="checkbox" name="members" value="${user[0]}" checked/> ${email}
                            %else:
                              <input type="checkbox" name="members" value="${user[0]}"/> ${email}
                            %endif
                            <% 
                              anchor_loc = anchors.index( anchor )
                              break 
                            %>
                          %endif
                        %endfor
                      %endif
                    </td>
                    <% ctr += 1 %>
                  %endfor
                </td>
              </tr>
            %endif
            <tr><td><center><button name="action" value="update_group_members">Update Membership</button></center></td></tr>
          </form>
        </table>
      </td>
    </tr>
  </table>
</div>
