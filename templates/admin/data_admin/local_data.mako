<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
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
<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>
<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
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
<style type="text/css">
    .params-block { display: none; }
    td, th { padding-left: 10px; padding-right: 10px; }
    td.Generate { text-decoration: underline; background-color: #EEEEEE; }
    td.Generating { text-decoration: none; background-color: #FFFFCC; }
    td.Generated { background-color: #CCFFCC; }
</style>
<div class="toolForm">
    %if message:
        <div class="${status}">${message}</div>
    %endif
    <div class="toolFormTitle">Currently tracked builds <a class="action-button" href="/data_admin/add_genome">Add new</a></div>
    <div class="toolFormBody">
        <h2>Locally cached data:</h2>
        <h3>NOTE: Indexers queued here will not be reflected in the table until Galaxy is restarted.</h3>
        <table id="locfiles">
            <tr><th>Database ID</th><th>Name</th><th>Bowtie</th><th>Bowtie 2</th><th>BWA</th><th>Sam</th><th>Picard</th><th>PerM</th></tr>
            %for dbkey in sorted(genomes.keys()):
                <tr>
                    <td>${dbkey}</td>
                    <td>${genomes[dbkey]['name']}</td>
                    <td id="${dbkey}-bowtie" class="indexcell ${genomes[dbkey]['bowtie_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="bowtie" data-dbkey="${dbkey}">${genomes[dbkey]['bowtie_indexes']}</td>
                    <td id="${dbkey}-bowtie2" class="indexcell ${genomes[dbkey]['bowtie2_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="bowtie2" data-dbkey="${dbkey}">${genomes[dbkey]['bowtie2_indexes']}</td>
                    <td id="${dbkey}-bwa" class="indexcell ${genomes[dbkey]['bwa_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="bwa" data-dbkey="${dbkey}">${genomes[dbkey]['bwa_indexes']}</td>
                    <td id="${dbkey}-sam" class="indexcell ${genomes[dbkey]['sam_fa_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="sam" data-dbkey="${dbkey}">${genomes[dbkey]['sam_fa_indexes']}</td>
                    <td id="${dbkey}-picard" class="indexcell ${genomes[dbkey]['srma_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="picard" data-dbkey="${dbkey}">${genomes[dbkey]['srma_indexes']}</td>
                    <td id="${dbkey}-perm" class="indexcell ${genomes[dbkey]['perm_base_indexes']}" data-fapath="${genomes[dbkey]['fapath']}" data-longname="${genomes[dbkey]['name']}" data-index="perm" data-dbkey="${dbkey}">${genomes[dbkey]['perm_base_indexes']}</td>
                </tr>
            %endfor
        </table>
        <h2>Recent jobs:</h2>
        <p>Click the job ID to see job details. Note that this list only shows jobs initiated by your account.</p>
        <div id="recentJobs">
        %for job in jobgrid:
            <div id="job-${job['deferred']}" data-dbkey="${job['dbkey']}" data-name="${job['intname']}" data-indexes="${job['indexers']}" data-jobid="${job['deferred']}" data-state="${job['state']}" class="historyItem-${job['state']} historyItemWrapper historyItem">
                <p>Job ID <a href="${h.url_for( controller='data_admin', action='monitor_status', job=job['deferred'] )}">${job['deferred']}</a>:
                %if job['jobtype'] == 'download':
                    Download <em>${job['intname']}</em>
                    %if job['indexers']:
                    and index with ${job['indexers']}
                    %endif
                %else:
                    Index <em>${job['intname']}</em> with ${job['indexers']}
                %endif
                </p>
            </div>
        %endfor
        </div>
</div>
<script type="text/javascript">
    finalstates = new Array('done', 'error', 'ok');
    $('.indexcell').click(function() {
        status = $(this).html();
        elem = $(this);
        if (status != 'Generate') {
            return;
        }
        longname = $(this).attr('data-longname');
        dbkey = $(this).attr('data-dbkey');
        indexes = $(this).attr('data-index');
        path = $(this).attr('data-fapath');
        $.post('${h.url_for( controller='data_admin', action='index_build' )}', { longname: longname, dbkey: dbkey, indexes: indexes, path: path }, function(data) {
            if (data == 'ERROR') {
                alert('There was an error.');
            }
            else {
                elem.html('Generating');
                elem.attr('class', 'indexcell Generating');
            }
            newhtml = '<div data-dbkey="' + dbkey + '" data-name="' + longname + '" data-indexes="' + indexes + '" id="job-' + data + '" class="historyItem-new historyItemWrapper historyItem">' +
                '<p>Job ID <a href="${h.url_for( controller='data_admin', action='monitor_status')}?job=' + data + '">' + data + '</a>: ' +
                'Index <em>' + longname + '</em> with ' + indexes + '</p></div>';
            $('#recentJobs').prepend(newhtml);
            $('#job-' + data).delay(3000).queue(function(n) {
                checkJob(data);
                n();
            });
        });
    });
    
    function checkJob(jobid) {
        $.get('${h.url_for( controller='data_admin', action='get_jobs' )}', { jobid: jobid }, function(data) {
            jsondata = JSON.parse(data)[0];
            jsondata["name"] = $('#job-' + jobid).attr('data-name');
            jsondata["dbkey"] = $('#job-' + jobid).attr('data-dbkey');
            jsondata["indexes"] = $('#job-' + jobid).attr('data-indexes');
            newhtml = makeNewHTML(jsondata);
            $('#job-' + jobid).replaceWith(newhtml);
            if ($.inArray(jsondata["status"], finalstates) == -1) {
                $('#job-' + jobid).delay(3000).queue(function(n) {
                    checkJob(jobid);
                    n();
                });
            }
            if (jsondata["status"] == 'done' || jsondata["status"] == 'ok') {
                elem = $('#' + jsondata["dbkey"] + '-' + jsondata["indexes"]);
                elem.html('Generated');
                elem.attr('class', 'indexcell Generated');
            }
        });
    }
    
    function makeNewHTML(jsondata) {
        newhtml = '<div data-dbkey="' + jsondata["dbkey"] + '" data-name="' + jsondata["name"] + '" data-indexes="' + jsondata["indexes"] + '" id="job-' + jsondata["jobid"] + '" class="historyItem-' + jsondata["status"] + ' historyItemWrapper historyItem">' +
            '<p>Job ID <a href="${h.url_for( controller='data_admin', action='monitor_status')}?job=' + jsondata["jobid"] + '">' + jsondata["jobid"] + '</a>: ' +
            'Index <em>' + jsondata["name"] + '</em> with ' + jsondata["indexes"] + '</p></div>';
        return newhtml;
    }
    
    $(document).ready(function() {
        $('.historyItem').each(function() {
            state = $(this).attr('data-state');
            jobid = $(this).attr('data-jobid');
            if ($.inArray(state, finalstates) == -1) {
                checkJob(jobid);
            }
        });
    });

</script>