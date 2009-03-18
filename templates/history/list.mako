<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">${_('Your saved histories')}</%def>

%if message:
    <p>
        <div class="${message_type}message transient-message">${message}</div>
        <div style="clear: both"></div>
    </p>
%endif

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        %if refresh_history:
            if ( parent.frames && parent.frames.galaxy_history ) {
                parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
            }
        %endif
        
        ## TODO: generalize and move into galaxy.base.js
        $(function() {
            $(".grid").each( function() {
                var grid = this;
                var checkboxes = $(this).find("input.grid-row-select-checkbox");
                var update = $(this).find( "span.grid-selected-count" );
                $(checkboxes).each( function() {
                    $(this).change( function() {
                        var n = $(checkboxes).filter("[checked]").size();
                        update.text( n );
                    });
                })
            });
        });
        
    </script>
</%def>

<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <style>
        .count-box {
            width: 1.1em;
            float: left;
            padding: 5px;
            margin-right: 5px;
            border-width: 1px;
            border-style: solid;
            text-align: center;
        }
        .count-box-dummy {
            width: 1.1em;
            float: left;
            padding: 5px;
            margin-right: 5px;
            border-width: 1px;
            border-style: solid;
            border-color: transparent;
            background: transparent;
            text-align: center;
        }
    </style>
</%def>


<h2>${_('Stored Histories')}</h2>

<ul class="manage-table-actions">
    <li>
        %if show_deleted:
            <a href="${h.url_for( show_deleted=False )}" class="action-button">${_('Hide deleted')}</a></div>
        %else:
            <a href="${h.url_for( show_deleted=True )}" class="action-button">${_('Show deleted')}</a></div>
        %endif
    </li>
</ul>

<form name="history_actions" action="${h.url_for()}" method="post" >
    %if show_deleted:
        <input type="hidden" name="show_deleted" value="true">
    %endif
    
    <table class="grid">
        <thead>
            <tr>
                <th width="1.5em"></th>
                <th>Name (click to activate)</th>
                <th>Datasets (by state)</th>
                <th>Status</th>
                <th>Last update</th>
                <th></th>
            </tr>
        </thead>
        
        <tbody>
            
            %for i, history in enumerate( user.histories ):
    
                %if ( show_deleted and not history.purged ) or not( history.deleted ):
    
                    <tr class="${["","current"][ history == trans.get_history() ]}">
    
                        <td><input type="checkbox" name="id" value="${history.id}" class="grid-row-select-checkbox"></td>
                    
                        <td>
                            %if not history.deleted:
                                <a href="${h.url_for( operation="switch", id=history.id, show_deleted=show_deleted )}">${history.name}</a>
                                <a id="h-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                            %else:
                                ${history.name} <a id="h-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a> 
                            %endif
                        </td>
              
                        <td>
              
                            <%
                              total_ok = sum( 1 for d in history.active_datasets if d.state == 'ok' )
                              total_running = sum( 1 for d in history.active_datasets if d.state == 'running' )
                              total_queued = sum( 1 for d in history.active_datasets if d.state == 'queued' )
                              total_error = sum( 1 for d in history.active_datasets if d.state == 'error' )
                            %>
              
                            %if total_ok:
                                <div class="count-box state-color-ok">${total_ok}</div>
                            %else:
                                <div class="count-box-dummy"></div>
                            %endif
                            
                            %if total_error:
                                <div class="count-box state-color-error">${total_error}</div
                            %else:
                                <div class="count-box-dummy"></div>
                            %endif
                            
                            %if total_running:
                                <div class="count-box state-color-running">${total_running}</div>
                            %else:
                                <div class="count-box-dummy"></div>
                            %endif
                            
                            %if total_queued:
                                <div class="count-box state-color-queued">${total_queued}</div>
                            %else:
                                <div class="count-box-dummy"></div>
                            %endif
              
                        </td>
              
                        <td>
                            %if history == trans.get_history():
                                active
                            %endif
                            %if history.deleted:
                                deleted
                            %endif
                        </td>
              
                        <td>${h.date.distance_of_time_in_words( history.update_time, h.date.datetime.utcnow() )}</td>
    
                        <td>
                            <div popupmenu="h-${i}-popup">
                                
                                %if not history.deleted:
                                    <a class="action-button" href="${h.url_for( operation='rename', id=history.id, show_deleted=show_deleted )}">${_('rename')}</a> <br />
                                    <a class="action-button" href="${h.url_for( operation='switch', id=history.id, show_deleted=show_deleted )}">${_('switch to')}</a> <br />
                                    <a class="action-button" href="${h.url_for( operation='delete', id=history.id , show_deleted=show_deleted)}" confirm="Are you sure you want to delete this history?">${_('delete')}</a> <br />
                                %else:
                                    <a class="action-button" href="${h.url_for( operation='undelete', id=history.id, show_deleted=show_deleted )}">${_('undelete')}</a><br />
                                %endif
              
                            </div>
                        </td>
                        
                    </tr>
                
                %endif
                                
            %endfor
        
        </tbody>
        <tfoot>
            <tr>
                <td></td>
                <td colspan="6">
                    For <span class="grid-selected-count"></span> selected histories:
                    <input type="submit" name="operation" value="Share" class="action-button">
                    <input type="submit" name="operation" value="Rename" class="action-button">
                    <input type="submit" name="operation" value="Delete" class="action-button">
                    %if show_deleted:
                    <input type="submit" name="operation" value="${_('Undelete')}" class="action-button">   
                    %endif
                </td>
            </tr>
        </tfoot>
    </table>
  </form>
