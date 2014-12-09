<%inherit file="/base.mako"/>
<%page expression_filter="h"/>

<div class="donemessagelarge">
%if scheduled:
    Successfully ran workflow "${util.unicodify( workflow.name )}". The following datasets have been added to the queue:
    %for invocation in invocations:
        <div class="workflow-invocation-complete">
            %if invocation['new_history']:
                <p>These datasets will appear in a new history:
                <a target='galaxy_history' href="${h.url_for( controller='history', action='list', operation="Switch", id=trans.security.encode_id(invocation['new_history'].id), use_panels=False, show_deleted=False ) | n}">
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
    if( top.Galaxy && top.Galaxy.currHistoryPanel ){
        top.Galaxy.currHistoryPanel.refreshContents();
    }
</script>
