define([
    'utils/graph',
    'utils/add-logging'
],function( GRAPH, addLogging ){
// ============================================================================
var _super = GRAPH.Graph;
var JobDAG = function( options ){
    var self = this;
    //this.logger = console;

    // instance vars
//TODO: needed?
    self._historyContentsMap = {};
    self.filters = [];

    self._idMap = {};
    self.noInputJobs = [];
    self.noOutputJobs = [];

//TODO: save these?
    self.filteredSetMetadata = [];
    self.filteredErroredJobs = [];

    _super.call( self, true, null, options );
};
JobDAG.prototype = new GRAPH.Graph();
JobDAG.prototype.constructor = JobDAG;
addLogging( JobDAG );

// ----------------------------------------------------------------------------
JobDAG.prototype.init = function _init( options ){
    options = options || {};
    _super.prototype.init.call( this, options );

    var self = this,
        historyContentsJSON = options.historyContents || [];
        jobsJSON = options.jobs || [];

    historyContentsJSON.forEach( function( content, i ){
        self._historyContentsMap[ content.id ] = _.clone( content );
    });

    self.options = _.defaults( _.omit( options, 'historyContents', 'jobs' ), {
        excludeSetMetadata : false
    });
    self.filters = self._initFilters();

//TODO: O( 3N )
    self.preprocessJobs( _.clone( jobsJSON ) );
    self.createGraph();

    return self;
};

JobDAG.prototype._initFilters = function __initFilters(){
    var self = this,
        filters = [];

    if( self.options.excludeSetMetadata ){
        self.filteredSetMetadata = [];
        filters.push( function filterSetMetadata( jobData ){
            if( jobData.job.tool_id !== '__SET_METADATA__' ){ return true; }
            self.filteredSetMetadata.push( jobData.job.id );
            return false;
        });
    }

    if( self.options.excludeErroredJobs ){
        self.filteredErroredJobs = [];
        filters.push( function filterErrored( jobData ){
            if( jobData.job.state !== 'error' ){ return true; }
            self.filteredErroredJobs.push( jobData.job.id );
            return false;
        });
    }

    // all outputs deleted
    // all outputs hidden

    if( _.isArray( self.options.filters ) ){
        filters = filters.concat( self.options.filters );
    }
    self.debug( 'filters len:', filters.length );
    return filters;
};

JobDAG.prototype.preprocessJobs = function _preprocessJobs( jobs ){
    this.info( 'processing jobs' );

    var self = this;
//TODO:? sorting neccessary?
    self.sort( jobs ).forEach( function( job, i ){
        var jobData = self.preprocessJob( job, i );
        if( jobData ){
            self._idMap[ job.id ] = jobData;
        }
    });
    return self;
};

JobDAG.prototype.sort = function _sort( jobs ){
    function cmpCreate( a, b ){
        if( a.update_time > b.update_time ){ return 1; }
        if( a.update_time < b.update_time ){ return -1; }
        return 0;
    }
    return jobs.sort( cmpCreate );
};

JobDAG.prototype.preprocessJob = function _preprocessJob( job, index ){
    //this.info( 'preprocessJob', job, index );
    var self = this,
        jobData = { index: index, job: job };

    jobData.inputs = self.datasetMapToIdArray( job.inputs, function( dataset, nameInJob ){
        //TODO:? store output name in self._datasets[ output.id ] from creating job?
    });
    if( jobData.inputs.length === 0 ){
        self.noInputJobs.push( job.id );
    }
    jobData.outputs = self.datasetMapToIdArray( job.outputs, function( dataset, nameInJob ){

    });
    if( jobData.outputs.length === 0 ){
        self.noOutputJobs.push( job.id );
    }

    //self.debug( JSON.stringify( jobData, null, '  ' ) );
    // apply filters after processing job allowing access to the additional data above in the filters
    for( var i=0; i<self.filters.length; i++ ){
        if( !self.filters[i].call( self, jobData ) ){
            self.debug( 'job', job.id, ' has been filtered out by function:\n', self.filters[i] );
            return null;
        }
    }

    //self.info( 'preprocessJob returning', jobData );
    return jobData;
};

JobDAG.prototype.datasetMapToIdArray = function _datasetMapToIdArray( datasetMap, processFn ){
    var self = this;
    return _.map( datasetMap, function( dataset, nameInJob ){
        if( !dataset.id ){
            throw new Error( 'No id on datasetMap: ', JSON.stringify( dataset ) );
        }
        if( !dataset.src || dataset.src !== 'hda' ){
            throw new Error( 'Bad src on datasetMap: ', JSON.stringify( dataset ) );
        }
        processFn.call( self, dataset, nameInJob );
        return dataset.id;
    });
};

JobDAG.prototype.createGraph = function _createGraph(){
    var self = this;
    self.debug( 'connections:' );

    _.each( self._idMap, function( sourceJobData, sourceJobId ){
        self.debug( '\t', sourceJobId, sourceJobData );
        self.createVertex( sourceJobId, sourceJobData );

        sourceJobData.usedIn = [];
        _.each( sourceJobData.outputs, function( outputDatasetId ){
//TODO: O(n^2)
            _.each( self._idMap, function( targetJobData, targetJobId ){
                if( targetJobData === sourceJobData ){ return; }

                if( targetJobData.inputs.indexOf( outputDatasetId ) !== -1 ){
                    self.info( '\t\t\t found connection: ', sourceJobId, targetJobId );
                    sourceJobData.usedIn.push({ job: targetJobId, output: outputDatasetId });

                    self.createVertex( targetJobId, targetJobData );

                    self.createEdge( sourceJobId, targetJobId, self.directed, {
                        dataset : outputDatasetId
                    });
                }
            });
        });
    });
    self.debug( 'job data: ', JSON.stringify( self._idMap, null, '  ' ) );
    return self;
};

Graph.prototype.weakComponentGraphArray = function(){
    return this.weakComponents().map( function( component ){
//TODO: this seems to belong above (in sort) - why isn't it preserved?
        component.vertices.sort( function cmpCreate( a, b ){
            if( a.data.job.update_time > b.data.job.update_time ){ return 1; }
            if( a.data.job.update_time < b.data.job.update_time ){ return -1; }
            return 0;
        });
        return new Graph( this.directed, component );
    });
};


// ============================================================================
    return JobDAG;
    //return {
    //    jobDAG : jobDAG
    //};
});
