<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<%def name="title()">Create Group</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <h3 align="center">Create Group</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr>
      <td>
        <table border="0">            
          <form name="group_create" action="${h.url_for( controller='admin', action='new_group' )}" method="post" >
            <tr>
              <td>Name: <input  name="name" type="textfield" value="" size=40"></td>
            </tr>
            %if len( users ) == 0:
              <tr><td>There are no Galaxy users</td></tr>
            %else:
              <% 
                render_quick_find = len( users ) > 50
              %>
              %if render_quick_find:
                <%
                  anchors = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
                  anchor_loc = 0
                  anchored = False
                  curr_anchor = 'A'
                %>
                <tr class="header"><td><a name="TOP">Add Members to Group - Quick Find</a></td></tr>
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
                <tr class="header"><td>Add Members to Group</td></tr>
              %endif
              <tr>
                <td>
                  %for user in users:
                    <% email = unescape( user[1], unentities ) %>
                    %if render_quick_find and not email.upper().startswith( curr_anchor ):
                      <% anchored = False %>
                    %endif
                    <tr>
                      <td>  
                        %if render_quick_find and email.upper().startswith( curr_anchor ):
                          %if not anchored:
                            <a name="${curr_anchor}"></a>
                            <hr/>
                            <div style="float: right;"><a href="#TOP">quick find</a></div>
                            <br/>
                            <% anchored = True %>
                          %endif
                          <input type="checkbox" name="members" value="${user[0]}"/> ${email}
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
                              <input type="checkbox" name="members" value="${user[0]}"/> ${email}
                              <% 
                                anchor_loc = anchors.index( anchor )
                                break 
                              %>
                            %endif
                          %endfor
                        %else:
                          <input type="checkbox" name="members" value="${user[0]}"/> ${email}
                        %endif
                      </td>
                    </tr>
                  %endfor
                </td>
              </tr>
            %endif
            <tr><td><center><button name="create_group_button" value="group_create">Create</button></center></td></tr>
          </form>
        </table>
      </td>
    </tr>
  </table>
</div>
