<%namespace file="/library/common/library_item_info.mako" import="render_library_item_info" />
<%namespace file="/library/common/common.mako" import="render_actions_on_multiple_items" />
<%namespace file="/library/common/common.mako" import="render_compression_types_help" />
<%namespace file="/library/common/common.mako" import="common_javascripts" />

<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
    self.has_accessible_datasets = False
%>
</%def>

##
## Override methods from base.mako and base_panels.mako
##
<%def name="center_panel()">
   <div style="overflow: auto; height: 100%;">
       <div class="page-container" style="padding: 10px;">
           ${render_content()}
       </div>
   </div>
</%def>
<p>The genome build and any selected indexers have been added to the job queue. Below you will see the status of each job.</p>
<div id="jobStatus" data-job="${mainjob}">
%for jobentry in jobs:
    <div class="${jobentry['style']} dialog-box" id="job${jobentry['jobid']}" data-state="${jobentry['state']}" data-jobid="${jobentry['jobid']}" data-type="${jobentry['type']}">
        <span class="inline">${jobentry['type']}</span>
    </div>
%endfor
</div>
<a href="${h.url_for( controller='data_admin', action='manage_data' )}">Return to the download form</a>
<script type="text/javascript">
    function getNewHtml(jobid) {
        $.get('${h.url_for( controller='data_admin', action='ajax_statusupdate' )}', { jobid: jobid }, function(data) {
            $('#jobStatus').html(data);
        });
        $('#jobStatus').children().each(function() {
            state = $(this).attr('class');
            //alert(state);
            if (state != 'panel-done-message dialog-box' && state != 'panel-error-message dialog-box') {
                setJobRefreshers();
                return;
            }
        });
    }
    function setJobRefreshers() {
        $('#jobStatus').delay(3000).queue(function(n) { getNewHtml($(this).attr('data-job')); n(); }).fadeIn(750);
    }
    $(document).ready(function() {
        setJobRefreshers();
    });
</script>