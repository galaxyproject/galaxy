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
    ${h.js("libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging" )}
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
</style>
<div class="toolForm">
    %if message:
        <div class="${status}">${message}</div>
    %endif
    <div class="toolFormTitle">Get build from a remote server</div>
    <div class="toolFormBody">
    <form name="download_build" action="${h.url_for( controller='data_admin', action='download_build' )}" enctype="multipart/form-data" method="post">
        <div class="form-row">
            <label for="source">Data Source</label>
            <select id="datasource" name="source" label="Data Source">
                <option value="UCSC">UCSC</option>
                <option value="URL">Direct Link</option>
                <option value="NCBI">NCBI</option>
                <option value="Ensembl">EnsemblGenome</option>
            </select>
            <div style="clear: both;">&nbsp;</div>
        </div>
        <div class="form-row">
            <label for="indexers">Indexers</label>
            <select name="indexers" multiple style="width: 200px; height: 125px;">
                <option value="2bit" selected>TwoBit</option>
                <option value="bowtie">Bowtie</option>
                <option value="bowtie2">Bowtie 2</option>
                <option value="bwa">BWA</option>
                <option value="perm">PerM</option>
                <option value="picard">Picard</option>
                <option value="sam">sam</option>
            </select>
            <div class="toolParamHelp" style="clear: both;">
                Select the indexers you want to run on the FASTA file after downloading.
            </div>
        </div>
        <h2>Parameters</h2>
        <div id="params_URL" class="params-block">
            <div class="form-row">
                <label for="longname">Long Name</label>
                <input name="longname" type="text" label="Long Name" />
                <div style="clear: both;">&nbsp;</div>
                <div class="toolParamHelp" style="clear: both;">
                    A descriptive name for this build.
                </div>
            </div>
            <div class="form-row">
                <label for="url_dbkey">DB Key</label>
                <input name="url_dbkey" type="text" label="DB Key" />
                <div style="clear: both;">&nbsp;</div>
                <div class="toolParamHelp" style="clear: both;">
                    The internal DB key for this build. WARNING: Using a value that already exists in one or more .loc files may have unpredictable results.
                </div>
            </div>
            <div id="dlparams">
                <div class="form-row">
                    <label for="url">URL</label>
                    <input name="url" type="text" label="URL" />
                    <div style="clear: both;">&nbsp;</div>
                    <div class="toolParamHelp" style="clear: both;">
                        The URL to download this build from.
                    </div>
                </div>
            </div>
        </div>
        <div id="params_NCBI" class="params-block">
            <div class="form-row">
                <label>Genome:</label>
                <div class="form-row-input">
                    <input type="text" class="text-and-autocomplete-select ac_input" size="40" name="ncbi_name" id="ncbi_name" value="" />
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    If you can't find the build you want in this list, open a terminal and execute
                    <pre>sh cron/updatencbi.sh</pre>
                    in your galaxy root directory.
                </div>
            </div>
        </div>
        <div id="params_Ensembl" class="params-block">
            <div class="form-row">
                <label>Genome:</label>
                <div class="form-row-input">
                    <select name="ensembl_dbkey" last_selected_value="?">
                        %for dbkey in ensembls:
                            <option value="${dbkey['dbkey']}">${dbkey['dbkey']} - ${dbkey['name']}</option>
                        %endfor
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    If you can't find the build you want in this list, open a terminal and execute
                    <pre>sh cron/updateensembl.sh</pre>
                    in your galaxy root directory.
                </div>
            </div>
        </div>
        <div id="params_UCSC" class="params-block">
            <div class="form-row">
                <label>Genome:</label>
                <div class="form-row-input">
                    <select name="dbkey" last_selected_value="?">
                        %for dbkey in dbkeys:
                            %if dbkey[0] == last_used_build:
                                <option value="${dbkey[0]}" selected>${dbkey[1]}</option>
                            %else:
                                <option value="${dbkey[0]}">${dbkey[1]}</option>
                            %endif
                        %endfor
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    If you can't find the build you want in this list, open a terminal and execute
                    <pre>sh cron/updateucsc.sh</pre>
                    in your galaxy root directory.
                </div>
            </div>
        </div>
        <div class="form-row">
            <input type="submit" class="primary-button" name="runtool_btn" value="Download and index"/>
        </div>
        <script type="text/javascript">
            $(document).ready(function() {
                checkDataSource();
            });
            $('#datasource').change(function() {
                checkDataSource();
            });
            function checkDataSource() {
                var ds = $('#datasource').val();
                $('.params-block').each(function() {
                    $(this).hide();
                });
                $('#params_' + ds).show();
            };
            
            var ac = $('#ncbi_name').autocomplete( $('#ncbi_name'), { minChars: 3, max: 100, url: '${h.url_for( controller='data_admin', action='genome_search' )}' } );
        </script>
    </form>
</div>
