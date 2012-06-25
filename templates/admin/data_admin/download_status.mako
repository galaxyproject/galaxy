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
<p>${name} been added to the job queue
    %if indexers:
        to be indexed with ${indexers}
    %endif
    </p>
<table id="jobStatus">
</table>
<p><a href="${h.url_for( controller='data_admin', action='manage_data' )}">Overview</a>.</p>
<p><a href="${h.url_for( controller='data_admin', action='add_genome' )}">Download form</a>.</p>
<script type="text/javascript">
    jobs = ${jsonjobs}
    finalstates = new Array('done', 'error', 'ok');
    
    function makeHTML(jobrow) {
        jc = 'jobrow ' + jobrow['style'];
        djid = jobrow['jobid'];
        jt = jobrow['type'];
        idval = jt + '-job-' + djid;
        return '<tr id="' + idval + '" class="' + jc + '" data-status="' + jobrow['status'] + '" data-jobid="' + djid + '" data-jobtype="' + jt + '">' +
               '<td style="padding: 0px 5px 0px 30px;">' + jobrow['label'] + '</td>' +
               '<td style="padding: 0px 5px;">' + jobrow['status'] + '</td></tr>';
    }
    
    function checkJobs() {
        var alldone = true;
        var mainjob;
        $('.jobrow').each(function() {
            status = $(this).attr('data-status');
            if ($(this).attr('data-jobtype') == 'deferred') {
                mainjob = $(this).attr('data-jobid');
            }
            if ($.inArray(status, finalstates) == -1) {
                alldone = false;
            }
        });
        if (!alldone) {
            checkForNewJobs(mainjob);
            $('#jobStatus').delay(3000).queue(function(n) {
                checkJobs();
                n();
            });
        }
    }
    
    function checkForNewJobs(mainjob) {
        $.get('${h.url_for( controller='data_admin', action='get_jobs' )}', { jobid: mainjob }, function(data) {
            jsondata = JSON.parse(data);
            for (i in jsondata) {
                currentjob = jsondata[i]
                if (jobs[i] == undefined) {
                    $('#jobStatus').append(makeHTML(jsondata[i]));
                    jobs.push(jsondata[i]);
                }
                $('#' + currentjob['type'] + '-job-' + currentjob['jobid']).replaceWith(makeHTML(currentjob));
            }
        });
    }
    
    $(document).ready(function() {
        for (job in jobs) {
            jobrow = jobs[job];
            $('#jobStatus').append(makeHTML(jobrow));
            if (jobrow['type'] == 'deferred') {
                $('#jobStatus').delay(5000).queue(function(n) {
                    checkForNewJobs(jobrow['jobid']);
                    n();
                }).fadeIn();
            }
        }
        $('#jobStatus').delay(3000).queue(function(n) { 
            checkJobs();
            n(); 
        }).fadeIn();
    });
</script>