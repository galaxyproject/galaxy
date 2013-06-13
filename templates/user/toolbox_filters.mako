<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif
</br>
</br>

<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='index', cntrller=cntrller )}">User preferences</a>
    </li>
</ul>

%if tool_filters or section_filters or label_filters:
    <div class="toolForm">
        <form name="toolbox_filter" id="toolbox_filter" action="${h.url_for( controller='user', action='edit_toolbox_filters', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
            % if tool_filters:
                <div class="toolFormTitle">Edit ToolBox filters :: Tools</div>
                <div class="toolFormBody">
                    % for filter in tool_filters:
                        <div class="form-row">
                            <div style="float: left; width: 40px; margin-right: 10px;">
                                % if filter['checked']:
                                    <input type="checkbox" name="t_${filter['filterpath']}" checked="checked">
                                % else:
                                    <input type="checkbox" name="t_${filter['filterpath']}">
                                % endif
                            </div>
                            <div style="float: left; margin-right: 10px;">
                                ${filter['short_desc']}
                                <div class="toolParamHelp" style="clear: both;">${filter['desc']}</div>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    % endfor
                </div>
            % endif

            % if section_filters:
                <div class="toolFormTitle">Edit ToolBox filters :: Sections</div>
                <div class="toolFormBody">
                    % for filter in section_filters:
                        <div class="form-row">
                            <div style="float: left; width: 40px; margin-right: 10px;">
                                % if filter['checked']:
                                    <input type="checkbox" name="s_${filter['filterpath']}" checked="checked">
                                % else:
                                    <input type="checkbox" name="s_${filter['filterpath']}">
                                % endif
                            </div>
                            <div style="float: left; margin-right: 10px;">
                                ${filter['short_desc']}
                                <div class="toolParamHelp" style="clear: both;">${filter['desc']}</div>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    % endfor
                </div>
            % endif

            % if label_filters:
                <div class="toolFormTitle">Edit ToolBox filters :: Labels</div>
                <div class="toolFormBody">
                    % for filter in label_filters:
                        <div class="form-row">
                            <div style="float: left; width: 40px; margin-right: 10px;">
                                % if filter['checked']:
                                    <input type="checkbox" name="l_${filter['filterpath']}" checked="checked">
                                % else:
                                    <input type="checkbox" name="l_${filter['filterpath']}">
                                % endif
                            </div>
                            <div style="float: left; margin-right: 10px;">
                                ${filter['short_desc']}
                                <div class="toolParamHelp" style="clear: both;">${filter['desc']}</div>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    % endfor
                </div>
            % endif
            <div class="form-row">
                <input type="submit" name="edit_toolbox_filter_button" value="Save changes">
            </div>
        </form>
    </div>
%else:
    ${render_msg( 'No filter available. Contact you system administrator or check your configuration file.', 'info' )}
%endif
