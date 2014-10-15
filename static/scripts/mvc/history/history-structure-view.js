define([
    'mvc/job/job-model',
    'mvc/job/job-li',
    'mvc/history/history-content-model',
    'mvc/history/job-dag',
    'mvc/base-mvc',
    'utils/localization',
    'libs/d3'
], function( JOB, JOB_LI, HISTORY_CONTENT, JobDAG, BASE_MVC, _l ){
// ============================================================================
/* TODO:
change component = this to something else

*/
// ============================================================================
/**
 *
 */
var HistoryStructureComponent = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({

    //logger : console,

    className : 'history-structure-component',

    initialize : function( attributes ){
        this.log( this + '(HistoryStructureComponent).initialize:', attributes );
        this.component = attributes.component;

        this._jobLiMap = {};
        this._createJobModels();

        this.layout = this._createLayout( attributes.layoutOptions );
    },

    _createJobModels : function(){
        var view = this;
        view.component.eachVertex( function( vertex ){
            var jobJSON = vertex.data.job,
                job = new JOB.Job( jobJSON );

            // get the models of the outputs for this job from the history
            var outputModels = _.map( job.get( 'outputs' ), function( output ){
                //note: output is { src: 'hda/dataset_collection', id: <some id> }
                // job output doesn't *quite* match up to normal typeId
                var type = output.src === 'hda'? 'dataset' : 'dataset_collection',
                    typeId = HISTORY_CONTENT.typeIdStr( type, output.id );
                return view.model.contents.get( typeId );
            });
            // set the collection (HistoryContents) for the job to that json (setting historyId for proper ajax urls)
            job.outputCollection.reset( outputModels );
            job.outputCollection.historyId = view.model.id;
            //this.debug( job.outputCollection );

            // create the bbone view for the job (to be positioned later accrd. to the layout) and cache
            var li = new JOB_LI.JobListItemView({ model: job, expanded: true });
            //var li = new JOB_LI.JobListItemView({ model: job });
            li.$el.appendTo( view.$el );
            view._jobLiMap[ job.id ] = li;
        });
        return view.jobs;
    },

    layoutDefaults : {
        paddingTop      : 8,
        paddingLeft     : 20,
        linkSpacing     : 16,
        jobHeight       : 308,
        jobWidthSpacing : 320,
        linkAdjX        : 4,
        linkAdjY        : 0
    },

    _createLayout : function( options ){
        options = _.defaults( _.clone( options || {} ), this.layoutDefaults );
        var view = this,
            vertices = _.values( view.component.vertices ),
            layout = _.extend( options, {
                nodeMap         : {},
                links           : [],
                el              : { width: 0, height: 0 },
                svg             : { width: 0, height: 0, top: 0, left: 0 }
            });

        vertices.forEach( function( v, j ){
            var node = { name: v.name, x: 0, y: 0 };
            layout.nodeMap[ v.name ] = node;
        });

        view.component.edges( function( e ){
            var link = {
                    source: e.source,
                    target: e.target
                };
            layout.links.push( link );
        });
        //this.debug( JSON.stringify( layout, null, '  ' ) );
        return layout;
    },

    _updateLayout : function(){
        var view = this,
            layout = view.layout;

        layout.svg.height = layout.paddingTop + ( layout.linkSpacing * _.size( layout.nodeMap ) );
        layout.el.height = layout.svg.height + layout.jobHeight;

//TODO:?? can't we just alter the component v and e's directly?
        // layout the job views putting jobWidthSpacing btwn each
        var x = layout.paddingLeft,
            y = layout.svg.height;
        _.each( layout.nodeMap, function( node, jobId ){
            //this.debug( node, jobId );
            node.x = x;
            node.y = y;
            x += layout.jobWidthSpacing;
        });
        layout.el.width = layout.svg.width = Math.max( layout.el.width, x );

        // layout the links - connecting each job by it's main coords (currently)
//TODO: somehow adjust the svg height based on the largest distance the longest connection needs
        layout.links.forEach( function( link ){
            var source = layout.nodeMap[ link.source ],
                target = layout.nodeMap[ link.target ];
            link.x1 = source.x + layout.linkAdjX;
            link.y1 = source.y + layout.linkAdjY;
            link.x2 = target.x + layout.linkAdjX;
            link.y2 = target.y + layout.linkAdjY;
        });
        //this.debug( JSON.stringify( layout, null, '  ' ) );
        return this.layout;
    },

    render : function( options ){
        this.log( this + '.renderComponent:', options );
        var view = this;

        view.component.eachVertex( function( v ){
            //TODO:? liMap needed - can't we attach to vertex?
            var li = view._jobLiMap[ v.name ];
            if( !li.$el.is( ':visible' ) ){
                li.render( 0 );
            }
        });

        view._updateLayout();
        // set up the display containers
        view.$el
            .width( view.layout.el.width )
            .height( view.layout.el.height );
        this.renderSVG();

        // position the job views accrd. to the layout
        view.component.eachVertex( function( v ){
            //TODO:? liMap needed - can't we attach to vertex?
            var li = view._jobLiMap[ v.name ],
                position = view.layout.nodeMap[ li.model.id ];
            //this.debug( position );
            li.$el.css({ top: position.y, left: position.x });
        });
        return this;
    },

    renderSVG : function(){
        var view = this,
            layout = view.layout;

        var svg = d3.select( this.el ).select( 'svg' );
        if( svg.empty() ){
            svg = d3.select( this.el ).append( 'svg' );
        }

        svg
            .attr( 'width', layout.svg.width )
            .attr( 'height', layout.svg.height );

        function highlightConnect( d ){
            d3.select( this ).classed( 'highlighted', true );
            view._jobLiMap[ d.source ].$el.addClass( 'highlighted' );
            view._jobLiMap[ d.target ].$el.addClass( 'highlighted' );
        }

        function unhighlightConnect( d ){
            d3.select( this ).classed( 'highlighted', false );
            view._jobLiMap[ d.source ].$el.removeClass( 'highlighted' );
            view._jobLiMap[ d.target ].$el.removeClass( 'highlighted' );
        }

        var connections = svg.selectAll( '.connection' )
                .data( layout.links );

        connections
            .enter().append( 'path' )
                .attr( 'class', 'connection' )
                .attr( 'id', function( d ){ return d.source + '-' + d.target; })
                .on( 'mouseover', highlightConnect )
                .on( 'mouseout', unhighlightConnect );

        connections.transition()
                .attr( 'd', function( d ){ return view._connectionPath( d ); });

//TODO: ? can we use tick here to update the links?
                
        return svg.node();
    },

    _connectionPath : function( d ){
        var CURVE_X = 0,
            controlY = ( ( d.x2 - d.x1 ) / this.layout.svg.width ) * this.layout.svg.height;
        return [
            'M', d.x1, ',', d.y1, ' ',
            'C',
                d.x1 + CURVE_X, ',', d.y1 - controlY, ' ',
                d.x2 - CURVE_X, ',', d.y2 - controlY, ' ',
            d.x2, ',', d.y2
        ].join( '' );
    },

    events : {
        'mouseover .job.list-item'  : function( ev ){ this.highlightConnected( ev.currentTarget, true ); },
        'mouseout .job.list-item'   : function( ev ){ this.highlightConnected( ev.currentTarget, false ); }
    },

    highlightConnected : function( jobElement, highlight ){
        highlight = highlight !== undefined? highlight : true;

        var view = this,
            component = view.component,
            jobClassFn = highlight? jQuery.prototype.addClass : jQuery.prototype.removeClass,
            connectionClass = highlight? 'connection highlighted' : 'connection';

        //console.debug( 'mouseover', this );
        var $jobs = jobClassFn.call( $( jobElement ), 'highlighted' ),
            id = $jobs.attr( 'id' ).replace( 'job-', '' );

        // immed. ancestors
        component.edges({ target: id }).forEach( function( edge ){
            jobClassFn.call( view.$( '#job-' + edge.source ), 'highlighted' );
            view.$( '#' + edge.source + '-' + id ).attr( 'class', connectionClass );
        });
        // descendants
        component.vertices[ id ].eachEdge( function( edge ){
            jobClassFn.call( view.$( '#job-' + edge.target ), 'highlighted' );
            view.$( '#' + id + '-' + edge.target ).attr( 'class', connectionClass );
        });
    },

    toString : function(){
        return 'HistoryStructureComponent(' + this.model.id + ')';
    }
});


// ============================================================================
/**
 *
 */
var VerticalHistoryStructureComponent = HistoryStructureComponent.extend({

    logger : console,

    className : HistoryStructureComponent.prototype.className + ' vertical',

    layoutDefaults : {
        paddingTop      : 8,
        paddingLeft     : 20,
        linkSpacing     : 16,
        jobWidth        : 308,
        jobHeight       : 308,
        initialSpacing  : 64,
        jobSpacing      : 16,
        linkAdjX        : 0,
        linkAdjY        : 4
    },

//TODO: how can we use the dom height of the job li's - they're not visible when this is called?
    _updateLayout : function(){
        var view = this,
            layout = view.layout;
        //this.info( this.cid, '_updateLayout' )

        layout.svg.width = layout.paddingLeft + ( layout.linkSpacing * _.size( layout.nodeMap ) );
        layout.el.width = layout.svg.width + layout.jobWidth;

        // reset height - we'll get the max Y below to assign to it
        layout.el.height = 0;

//TODO:?? can't we just alter the component v and e's directly?
        var x = layout.svg.width,
            y = layout.paddingTop;
        _.each( layout.nodeMap, function( node, jobId ){
            //this.debug( node, jobId );
            node.x = x;
            node.y = y;
            var li = view._jobLiMap[ jobId ];
            if( li.$el.is( ':visible' ) ){
                y += li.$el.height() + layout.jobSpacing;
            } else {
                y += layout.initialSpacing + layout.jobSpacing;
            }
        });
        layout.el.height = layout.svg.height = Math.max( layout.el.height, y );

        // layout the links - connecting each job by it's main coords (currently)
        layout.links.forEach( function( link ){
            var source = layout.nodeMap[ link.source ],
                target = layout.nodeMap[ link.target ];
            link.x1 = source.x + layout.linkAdjX;
            link.y1 = source.y + layout.linkAdjY;
            link.x2 = target.x + layout.linkAdjX;
            link.y2 = target.y + layout.linkAdjY;
            view.debug( 'link:', link.x1, link.y1, link.x2, link.y2, link );
        });
        //this.debug( JSON.stringify( layout, null, '  ' ) );
        view.debug( 'el:', layout.el );
        view.debug( 'svg:', layout.svg );
        return layout;
    },

    _connectionPath : function( d ){
        var CURVE_Y = 0,
            controlX = ( ( d.y2 - d.y1 ) / this.layout.svg.height ) * this.layout.svg.width;
        return [
            'M', d.x1, ',', d.y1, ' ',
            'C',
                d.x1 - controlX, ',', d.y1 + CURVE_Y, ' ',
                d.x2 - controlX, ',', d.y2 - CURVE_Y, ' ',
            d.x2, ',', d.y2
        ].join( '' );
    },

    toString : function(){
        return 'VerticalHistoryStructureComponent(' + this.model.id + ')';
    }
});


// ============================================================================
/**
 *
 */
var HistoryStructureView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({

    //logger : console,

    className : 'history-structure',

    initialize : function( attributes ){
        this.log( this + '(HistoryStructureView).initialize:', attributes, this.model );
//TODO: to model
        this.jobs = attributes.jobs;
        this._createDAG();
    },

    _createDAG : function(){
        this.dag = new JobDAG({
            historyContents     : this.model.contents.toJSON(),
            jobs                : this.jobs,
            excludeSetMetadata  : true,
            excludeErroredJobs  : true
        });
//window.dag = this.dag;
        this.log( this + '.dag:', this.dag );

        this._createComponents();
    },

    _createComponents : function(){
        this.log( this + '._createComponents' );
        var structure = this;
//window.structure = structure;

        structure.componentViews = structure.dag.weakComponentGraphArray().map( function( componentGraph ){
            return structure._createComponent( componentGraph );
        });
    },

    _createComponent : function( component ){
        this.log( this + '._createComponent:', component );
        return new HistoryStructureComponent({
        //return new VerticalHistoryStructureComponent({
                model       : this.model,
                component   : component
            });
    },

    render : function( options ){
        this.log( this + '.render:', options );
        var structure = this;

        structure.$el.html([
            '<div class="controls"></div>',
            '<div class="components"></div>'
        ].join( '' ));

        structure.componentViews.forEach( function( component ){
            component.render().$el.appendTo( structure.$components() );
        });
        return structure;
    },

    $components : function(){
        return this.$( '.components' );
    },

    toString : function(){
        return 'HistoryStructureView(' + ')';
    }
});


// ============================================================================
    return HistoryStructureView;
});
