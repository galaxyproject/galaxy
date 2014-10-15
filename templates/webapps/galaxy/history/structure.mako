<%inherit file="/base.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client" />

<%def name="title()">
    ${ ' | '.join([ history[ 'name' ], _( 'Structure' ) ]) }
</%def>

## -----------------------------------------------------------------------------
<%def name="stylesheets()">
${ parent.stylesheets() }

<style>
.history-structure-component {
    position: relative;
    margin-bottom: 8px;
}
.history-structure-component svg {
    /*background: rgba( 32, 96, 96, 0.5 );*/
    position: absolute;
}
.history-structure-component.vertical {
    /*border: 1px solid black;*/
    margin-right: 8px;
    float:left
}

.job.list-item {
    width: 300px;
    max-height: 300px;
    background: white;
    /* since #elements is position: relative, this top and left will be relative to it */
    position: absolute;
    overflow-y: auto;
    overflow-x: hidden;
    /*font-size: 80%;*/
    z-index: 1;
}
.job.list-item.highlighted {
    width: 306px;
    border: 4px solid black;
    margin-top: -3px;
    margin-left: -3px;
}


svg .connection {
    stroke-width: 4px;
    stroke: lightgrey;
    stroke-opacity: .6;
    fill: none;
}
svg .connection.highlighted {
    stroke: black;
    stroke-opacity: 1.0;
}


#dag-force-5 {
   background: rgba( 32, 96, 96, 0.5 );
}

.node text {
  pointer-events: none;
  font: 20px sans-serif;
  fill: #fff;
  text-anchor: middle;
}

.node circle {
  stroke: #fff;
  stroke-width: 1.5px;
}
.node.fixed circle {
  fill: #f00;
}

.link path {
  stroke: #555;
  stroke-opacity: .6;
}
marker {
  fill: #555;
  stroke-opacity: .6;
}

svg foreignObject {
    fill: red;
    stroke: black;
}

</style>
</%def>

<%def name="javascript_app()">
<script type="text/javascript">
/*
TODO:
    components should be graphs?
        as it is they're verts+edges

    in-panel view of anc desc

    show datasets when job not expanded
        make them external to the job display
    connect jobs by dataset
        which datasets from job X are which inputs in job Y?
    zoom out (somehow)
        move elems to SVG?
    (possibly) use foreignObject or svg instead of bbone/html overlay

    make job data human readable (needs tool data)

    use cases:
        hide thread
        isolate branch (hide other jobs) of thread
        create new thread from branch
        copy thread

    controls:
        (optionally) filter all deleted
        (optionally) filter all hidden
        (optionally) filter __SET_METADATA__
        (optionally) filter error'd jobs

    vertical layout
        will not allow expansion of jobs/datasets easily

    circular layout
        sources on inner radius

    challenges:
        expansion/view details of job or history
            could move to side panel
        difficult to scale dom (for zoomout)
            possible to use css transforms?
                transform svg and dom elements
                it is possible to use css transforms on svg nodes
                transforms are relative to centroid - need to adjust using translate as well
        syncing jquery anim and d3 anim difficult
            possible to use transitions?
                would need to update as jquery was expanding foreignObject/dom

*/


define( 'app', function(){
    require([
        'mvc/job/job-model',
        'mvc/history/history-model',
        'mvc/history/history-structure-view'
    ], function( JOB, HISTORY, StructureView ){

        var historyModel = new HISTORY.History( bootstrapped.history, bootstrapped.hdas );
window.historymodel = history;
window.jobs = bootstrapped.jobs;

        var structure = new StructureView({
            model   : historyModel,
            jobs    : bootstrapped.jobs
        });
        structure.$el.appendTo( 'body' );
        console.debug( 'structure visible?', structure.$el.is( ':visible' ) );
        structure.render();
window.structure = structure;

    });
});
</script>
${ galaxy_client.load( app='app', historyId=historyId, history=history, hdas=hdas, jobs=jobs ) }
</%def>
