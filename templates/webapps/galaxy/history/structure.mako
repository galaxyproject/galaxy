<%inherit file="/base.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client" />

<%def name="title()">
    ${ ' | '.join([ history[ 'name' ], _( 'Structure' ) ]) }
</%def>

## -----------------------------------------------------------------------------
<%def name="stylesheets()">
${ parent.stylesheets() }

<style>
.history-structure {
}

.history-structure-component {
    /*position: relative;*/
    border: 1px solid lightgrey;
    padding: 8px;
    margin-bottom: 8px;
    overflow: auto;
}
.history-structure-component.vertical {
    margin-right: 8px;
    float:left
}

.history-structure-component .graph {
    /*background: rgba( 96, 96, 32, 0.5 );*/
    transform-origin: top left;
    position: relative;
}

.history-structure-component .graph svg {
    /*background: rgba( 32, 96, 96, 0.5 );*/
    position: relative;
}

.history-structure-component .graph > .list-item {
    width: 300px;
    max-height: 300px;
    /* since .graph is position: relative, this top and left will be relative to it */
    position: absolute;
    overflow-y: auto;
    overflow-x: hidden;
    z-index: 1;
}
.history-structure-component .graph > .list-item.highlighted {
    width: 306px;
    border: 4px solid black;
    margin-top: -3px;
    margin-left: -3px;
}

.history-structure-component .graph svg .connection {
    stroke-width: 4px;
    stroke: lightgrey;
    stroke-opacity: .6;
    fill: none;
}
.history-structure-component .graph svg .connection.highlighted {
    stroke: black;
    stroke-opacity: 1.0;
}
</style>
</%def>

<%def name="javascript_app()">
<script type="text/javascript">
define( 'app', function(){
    require([
        'mvc/job/job-model',
        'mvc/history/history-model',
        'mvc/history/history-structure-view'
    ], function( JOB, HISTORY, StructureView ){

        var historyModel = new HISTORY.History( bootstrapped.history, bootstrapped.contents );
window.historymodel = historyModel;
window.jobs = bootstrapped.jobs;
window.tools = bootstrapped.tools;

        var structure = new StructureView({
            model   : historyModel,
            jobs    : bootstrapped.jobs,
            tools   : bootstrapped.tools
        });
window.structure = structure;
       structure.render().$el.appendTo( 'body' );
    });
});
</script>
${ galaxy_client.load( app='app', historyId=historyId, history=history, contents=contents, jobs=jobs, tools=tools ) }
</%def>
