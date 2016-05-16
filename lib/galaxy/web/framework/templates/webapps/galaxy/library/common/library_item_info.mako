<%def name="render_library_item_info( ldda )">
                            %if ldda.state == 'error':
                                <div class="libraryItem-${ldda.state | h}">Job error <i>(click name for more info)</i></div>
                            %elif ldda.state == 'queued':
                                <div class="libraryItem-${ldda.state | h}">This job is queued</div>
                            %elif ldda.state == 'running':
                                <div class="libraryItem-${ldda.state | h}">This job is running</div>
                            %elif ldda.state == 'upload':
                                <div class="libraryItem-${ldda.state | h}">This dataset is uploading</div>
                            %else:
                                ${ldda.message | h}
                            %endif
</%def>

${render_library_item_info( ldda )}
