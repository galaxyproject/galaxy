<%inherit file="/base.mako"/>

<div class="donemessagelarge">
    Successfully ran workflow "${workflow.name}". The following datasets have been added to the queue:
    %if new_history:
        These datasets will appear in a new history:
        <a target='galaxy_history' href="${h.url_for( controller='history', action='list', operation="Switch", id=trans.security.encode_id(new_history.id), use_panels=False, show_deleted=False )}">
            '${h.to_unicode(new_history.name)}'.
        </a>
    %endif
    <div style="padding-left: 10px;">
        %for step_outputs in outputs.itervalues():
            %for data in step_outputs.itervalues():
                %if not new_history or data.history == new_history:
                    <p><strong>${data.hid}</strong>: ${data.name}</p>
                %endif
            %endfor
        %endfor
    </div>
</div>

<script type="text/javascript">
  if ( parent.frames && parent.frames.galaxy_history ) {
      parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history' )}";
  }
</script>
