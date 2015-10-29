<%inherit file="/base.mako"/>
<%page expression_filter="h"/>

<div class="donemessagelarge">
%if scheduled:
    Successfully ran workflow "${util.unicodify( workflow.name )}". The following datasets have been added to the queue:
    %for invocation in invocations:
        <div class="workflow-invocation-complete">
            %if invocation['new_history']:
                <%
                    encoded_new_history = trans.security.encode_id(invocation['new_history'].id)
                %>
                <p>These datasets will appear in a new history:
                <a class='new-history-link' data-history-id="${encoded_new_history}" target='_top' href="${h.url_for( controller='history', action='switch_to_history', hist_id=encoded_new_history ) | n}">
                    '${h.to_unicode(invocation['new_history'].name)}'.
                </a></p>
            %endif
            <div style="padding-left: 10px;">
                %for step_outputs in invocation['outputs'].itervalues():
                    %for data in step_outputs.itervalues():
                        %if not invocation['new_history'] or data.history == invocation['new_history']:
                            <p><strong>${data.hid}</strong>: ${util.unicodify( data.name )}</p>
                        %endif
                    %endfor
                %endfor
            </div>
        </div>
    %endfor
%else:
    The requested workflows have been queued and datasets will appear
    as jobs are created - you will need to refresh your history panel
    to see these.
%endif
</div>

<script type="text/javascript">
    if(parent.Galaxy && parent.Galaxy.currHistoryPanel){
        parent.Galaxy.currHistoryPanel.refreshContents();
    }
    $('a.new-history-link').click(function(event){
        if(parent.Galaxy && parent.Galaxy.currHistoryPanel){
            event.preventDefault();
            parent.Galaxy.currHistoryPanel.switchToHistory($(this).data('history-id'));
        }
    });
</script>
