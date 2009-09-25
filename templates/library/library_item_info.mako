<%def name="render_library_item_info( ldda )">
                            %if ldda.state == 'error':
                                <div class="libraryItem-${ldda.state}">Job error <i>(click name for more info)</i></div>
                            %elif ldda.state == 'queued':
                                <div class="libraryItem-${ldda.state}">This job is queued</div>
                            %elif ldda.state == 'running':
                                <div class="libraryItem-${ldda.state}">This job is running</div>
                            %else:
                                ${ldda.message}
                            %endif
</%def>

${render_library_item_info( ldda )}
