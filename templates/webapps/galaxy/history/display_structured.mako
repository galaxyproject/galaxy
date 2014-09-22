<%inherit file="/base.mako"/>
<%namespace file="/show_params.mako" name="show_params" />

## ----------------------------------------------------------------------------
<%def name="title()">${ history.name } | ${ _( 'Structure' ) }</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">
        body {
            padding: 5px;
        }
        body > .workflow, body > .toolForm, body > .copied-from {
            /*width           : 80%;*/
            margin-bottom   : 8px;
            /*margin-left     : auto;*/
            /*margin-right    : auto;*/
        }
        .bold {
            font-weight: bold;
        }
        .light {
            font-weight: lighter;
            color: grey;
        }
        .right-aligned {
            text-align: right;
        }

        .clickable {
            cursor: pointer;
        }

        .workflow {
            border: solid gray 1px;
        }
        .workflow > .header {
            background: lightgray;
            padding: 5px 10px;
        }
        .workflow > .light {
            color: gray;
        }
        .workflow > .body {
            border-top: solid gray 1px;
        }
        .workflow > .body > .toolForm {
            border: 0px;
        }

        div.toolForm {
            border-width        : 1px;
            border-radius       : 0px;
        }
        .toolForm > .header {
            background-color: #EBD9B2;
            padding: 5px 10px;
        }
        .workflow div.toolForm:not(:first-child) .header {
            border-top: 1px solid #D6B161;
        }
        div.toolFormTitle {
            padding: 0px 0px 4px 0px;
            margin: 0px 0px 4px 0px;
            border: 0px;
            background-color: transparent;
            border-bottom: 1px solid #D6B161;
        }
        /* down from EBD9B2 --> 90743A */
        .toolFormTitle > .light {
            color: #90743A;
        }
        .toolForm em {
            color: #90743A;
        }

        .job-inputs {
            margin: 0px 6px 0px 6px;
            text-align: left;
        }
        .job-inputs td:nth-child(1) {
            text-align: right;
            font-weight: lighter;
            color: #90743A;
        }
        .job-inputs td:nth-child(1):after {
            content : ':'
        }
        .job-inputs td:nth-child(2) {
            padding-left: 4px;
        }
        .job-inputs em {
        }

        .job-inputs-show {
            float: right;
        }

        .copied-from {
            border: 1px solid lightgrey;
            border-width: 1px 1px 0px 1px;
        }
        .copied-from .header {
            border-bottom: 1px solid lightgrey;
            padding: 5px;
        }
        .copied-from .header .bold, .copied-from .header a {
            color: #888;
        }

        .dataset.hda {
            min-height  : 37px;
            border-width: 0px 0px 1px 0px;
        }
        .toolFormBody > .dataset.hda:last-child {
            border-bottom-width: 0px;
        }
        .dataset.hda:first-child {
            border-top: 1px solid #D6B161;
        }
        .dataset.hda .dataset-title-bar {
            padding-top: 8px;
            padding-left: 10px;
        }

    </style>
</%def>

## ----------------------------------------------------------------------------
<%def name="javascripts()">
<%
    self.js_app = 'display-structured'

    controller = trans.webapp.controllers[ 'history' ]
    hda_dicts = []
    id_hda_dict_map = {}
    for hda in history.active_datasets:
        hda_dict = controller.get_hda_dict( trans, hda )
        id_hda_dict_map[ hda_dict[ 'id' ] ] = hda_dict
        hda_dicts.append( hda_dict )
%>
    ${parent.javascripts()}

    ## load edit views for each of the hdas
    <script type="text/javascript">
        define( 'display-structured', function(){
            require([ 'mvc/history/hda-li-edit', 'mvc/history/hda-model' ], function( hdaEdit, hdaModel ){
                var hdaJSON = ${ h.dumps( hda_dicts, indent=( 2 if trans.debug else 0 ) ) };

                window.hdas = hdaJSON.map( function( hda ){
                    return new hdaEdit.HDAListItemEdit({
                        model           : new hdaModel.HistoryDatasetAssociation( hda ),
                        el              : $( '#hda-' + hda.id ),
                        linkTarget      : '_self',
                        purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                        logger          : Galaxy.logger
                    }).render( false );
                });
            });
        });

        $(function(){
            $( ".workflow, .tool" ).each( function(){
                var body = $( this ).children( ".body" );
                $( this ).children( ".header" ).click( function(){
                    body.toggle();
                }).addClass( "clickable" );
            });
            //$( ".job-inputs-show" ).click( function( ev ){
            //    ev.stopPropagation();
            //    $( this ).parent().siblings( '.job-inputs' ).toggle();
            //});
        });
    </script>
</%def>

## ----------------------------------------------------------------------------
<%def name="render_item( entity, children )">
<%
entity_name = entity.__class__.__name__
if entity_name == "HistoryDatasetAssociation":
    render_item_hda( entity, children )
elif entity_name == "Job":
    render_item_job( entity, children )
elif entity_name == "WorkflowInvocation":
    render_item_wf( entity, children )
%>
</%def>

## ---------------------------------------------------------------------------- hda
<%def name="render_item_hda( hda, children )">
## render hdas as a id'd stub for js to fill later

    %if hda.copied_from_history_dataset_association:
    ${ render_hda_copied_from_history( hda, children ) }

    %elif hda.copied_from_library_dataset_dataset_association:
    ${ render_hda_copied_from_library( hda, children ) }

    %else:
    <% id = trans.security.encode_id( hda.id ) %>
    <div id="hda-${id}" class="dataset hda state-${hda.state}"></div>
    %endif
</%def>

<%def name="render_hda_copied_from_history( hda, children )">
## wrap an hda in info about the history from where it was copied
    <% id = trans.security.encode_id( hda.id ) %>
    <% history_id = trans.security.encode_id( hda.copied_from_history_dataset_association.history_id ) %>
    <div class="copied-from copied-from-history">
        <div class="header">
            <div class="copied-from-dataset">
                <span class="light">${ _( 'Copied from history dataset' ) + ':' }</span>
                <span class="bold">${ hda.copied_from_history_dataset_association.name }</span>
            </div>
            <div class="copied-from-source">
                <span class="light">${ _( 'History' ) + ':' }</span>
                <span class="bold">
                    <a href="${ h.url_for( controller='history', action='view', id=history_id ) }">
                        ${ hda.copied_from_history_dataset_association.history.name }
                    </a>
                </span>
            </div>
        </div>
        <div id="hda-${id}" class="dataset hda state-${hda.state}"></div>
    </div>
</%def>

<%def name="render_hda_copied_from_library( hda, children )">
## wrap an hda in info about the library from where it was copied
    <% id = trans.security.encode_id( hda.id ) %>
    <%
        folder = hda.copied_from_library_dataset_dataset_association.library_dataset.folder
        folder_id = 'F' + trans.security.encode_id( folder.id )
    %>
    <div class="copied-from copied-from-library">
        <div class="header">
            <div class="copied-from-dataset">
                <span class="light">${ _( 'Copied from library dataset' ) + ':' }</span>
                <span class="bold">${ hda.copied_from_library_dataset_dataset_association.name }</span>
            </div>
            <div class="copied-from-source">
                <span class="light">${ _( 'Library' ) + ':' }</span>
                <span class="bold">
                    <a href="${ h.url_for( controller='library', action='list' ) + '#folders/F' + folder_id }">
                        ${ folder.name }
                    </a>
                </span>
            </div>
        </div>
        <div id="hda-${id}" class="dataset hda state-${hda.state}"></div>
    </div>
</%def>

## ---------------------------------------------------------------------------- job (and output hdas)
<%def name="render_item_job( job, children  )">
## render a job (as a toolForm) and its children (hdas)
    <div class="tool toolForm">
        <%
            tool = trans.app.toolbox.get_tool( job.tool_id )
            if tool:
                tool_name = tool.name
                tool_desc = tool.description
            else:
                tool_name = "Unknown tool with id '%s'" % job.tool_id
                tool_desc = ''

            params_object = None
            try:
                params_object = job.get_param_values( trans.app, ignore_errors=True )
            except Exception, exc:
                pass
        %>
        <div class="header">
            <div class="toolFormTitle">
                <span class="bold">${tool_name}</span>
                <span class="light">- ${tool_desc}</span>
                ##<a class="job-inputs-show" href="javascript:void(0)">${ _( "parameters" )}</a>
            </div>
            %if tool and params_object:
            <table class="job-inputs">
                ${ show_params.inputs_recursive( tool.inputs, params_object, depth=1 ) }
            </table>
            %else:
                <em>(${ _( 'No parameter data available' ) })</em>
            %endif
        </div>
        <div class="body toolFormBody">
        %for e, c in reversed( children ):
            ${render_item( e, c )}
        %endfor
        </div>
    </div>
</%def>

## ---------------------------------------------------------------------------- workflow (w/ jobs, hdas)
<%def name="render_item_wf( wf, children )">
## render a workflow and its children (jobs/toolForms)
    <div class="workflow">
        <div class="header">
            <span class="bold">${wf.workflow.name}</span>
            <span class="light">- Workflow</span>
        </div>
        <div class="body">
        %for e, c in reversed( children ):
            ${render_item( e, c )}
        %endfor
        </div>
    </div>
</%def>

## ---------------------------------------------------------------------------- body
## render all items from a dictionary prov. by history/display_structured
%for entity, children in items:
    ${render_item( entity, children )}
%endfor
