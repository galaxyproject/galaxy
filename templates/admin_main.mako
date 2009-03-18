<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">${_('Galaxy Administration')}</%def>

<table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
    <tr>
        <td>
            <h3 align="center">${_('Galaxy Administration')}</h3>
            %if msg:
                <p class="ok_bgr">${_(msg)}</p>
            %endif
        </td>
    </tr>
    <tr>
        <td>
            <form method="post" action="admin">
                <p>${_('Admin password: ')}<input type="password" name="passwd" size="8"></p>
                <p>
                    ${_('Reload tool: ')}
                    <select name="tool_id">
                        %for key, val in toolbox.tool_panel.items():
                            %if key.startswith( 'tool' ):
                                <option value="${val.id}">${_(val.name)}</option>
                            %elif key.startswith( 'section' ):
                                <optgroup label="${val.name}">
                                <% section = val %>
                                %for section_key, section_val in section.elems.items():
                                    %if section_key.startswith( 'tool' ):
                                        <option value="${section_val.id}">${_(section_val.name)}</option>
                                    %endif
                                %endfor
                            %endif
                        %endfor
                    </select>
                    <button name="action" value="tool_reload">${_('Reload')}</button>
                </p>
            </form>
        </td>
    </tr>
</table>
