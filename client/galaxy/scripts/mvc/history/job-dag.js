import _ from "underscore";
import GRAPH from "utils/graph";
import addLogging from "utils/add-logging";

// ============================================================================
var _super = GRAPH.Graph;
/** A Directed acyclic Graph built from a history's job data.
 *      Reads in job json, filters and process that json, and builds a graph
 *      using the connections between job inputs and outputs.
 */
var JobDAG = function(options) {
    options = options || {};
    var self = this;
    //this.logger = console;

    self.filters = [];

    // instance vars
    //TODO: needed?
    self._jobsData = [];
    self._historyContentsMap = {};
    self._toolMap = {};

    self._outputIdToJobMap = {};
    self.noInputJobs = [];
    self.noOutputJobs = [];

    //TODO: save these?
    self.filteredSetMetadata = [];
    self.filteredErroredJobs = [];

    self.dataKeys = ["jobs", "historyContents", "tools"];
    _super.call(self, true, _.pick(options, self.dataKeys), _.omit(options, self.dataKeys));
};
JobDAG.prototype = new GRAPH.Graph();
JobDAG.prototype.constructor = JobDAG;

// add logging ability - turn off/on using the this.logger statement above
addLogging(JobDAG);

// ----------------------------------------------------------------------------
/** process jobs, options, filters, and any history data, then create the graph */
JobDAG.prototype.init = function _init(options) {
    options = options || {};

    var self = this;
    self.options = _.defaults(options, {
        excludeSetMetadata: false
    });
    self.filters = self._initFilters();

    _super.prototype.init.call(self, options);
    return self;
};

/** add job filters based on options */
JobDAG.prototype._initFilters = function __initFilters() {
    var self = this;
    var filters = [];

    if (self.options.excludeSetMetadata) {
        self.filteredSetMetadata = [];
        filters.push(function filterSetMetadata(jobData) {
            if (jobData.job.tool_id !== "__SET_METADATA__") {
                return true;
            }
            self.filteredSetMetadata.push(jobData.job.id);
            return false;
        });
    }

    if (self.options.excludeErroredJobs) {
        self.filteredErroredJobs = [];
        filters.push(function filterErrored(jobData) {
            if (jobData.job.state !== "error") {
                return true;
            }
            self.filteredErroredJobs.push(jobData.job.id);
            return false;
        });
    }

    // all outputs deleted
    // all outputs hidden

    if (_.isArray(self.options.filters)) {
        filters = filters.concat(self.options.filters);
    }
    self.debug("filters len:", filters.length);
    return filters;
};

/**  */
JobDAG.prototype.read = function _read(data) {
    var self = this;
    if (_.has(data, "historyContents") && _.has(data, "jobs") && _.has(data, "tools")) {
        // a job dag is composed of these three elements:
        //  clone the 3 data sources into the DAG, processing the jobs finally using the history and tools
        self.preprocessHistoryContents(data.historyContents || [])
            .preprocessTools(data.tools || {})
            .preprocessJobs(data.jobs || []);

        // filter jobs and create the vertices and edges of the job DAG
        self.createGraph(self._filterJobs());
        return self;
    }
    return _super.prototype.read.call(this, data);
};

/**  */
JobDAG.prototype.preprocessHistoryContents = function _preprocessHistoryContents(historyContents) {
    this.info("processing history");
    var self = this;
    self._historyContentsMap = {};

    historyContents.forEach((content, i) => {
        self._historyContentsMap[content.id] = _.clone(content);
    });
    return self;
};

/**  */
JobDAG.prototype.preprocessTools = function _preprocessTools(tools) {
    this.info("processing tools");
    var self = this;
    self._toolMap = {};

    _.each(tools, (tool, id) => {
        self._toolMap[id] = _.clone(tool);
    });
    return self;
};

/** sort the cloned jobs, decorate with tool and history contents info, and store in prop array */
JobDAG.prototype.preprocessJobs = function _preprocessJobs(jobs) {
    this.info("processing jobs");
    var self = this;
    self._outputIdToJobMap = {};

    self._jobsData = self.sort(jobs).map(job => self.preprocessJob(_.clone(job)));
    //console.debug( JSON.stringify( self._jobsData, null, '    ' ) );
    //console.debug( JSON.stringify( self._outputIdToJobMap, null, '    ' ) );
    return self;
};

/** sort the jobs based on update time */
JobDAG.prototype.sort = function _sort(jobs) {
    function cmpCreate(a, b) {
        if (a.create_time > b.create_time) {
            return 1;
        }
        if (a.create_time < b.create_time) {
            return -1;
        }
        return 0;
    }
    return jobs.sort(cmpCreate);
};

/** decorate with input/output datasets and tool */
JobDAG.prototype.preprocessJob = function _preprocessJob(job, index) {
    //this.info( 'preprocessJob', job, index );
    var self = this;

    var jobData = { job: job };

    jobData.inputs = self._processInputs(job);
    if (_.size(jobData.inputs) === 0) {
        self.noInputJobs.push(job.id);
    }
    jobData.outputs = self._processOutputs(job);
    if (_.size(jobData.outputs) === 0) {
        self.noOutputJobs.push(job.id);
    }

    jobData.tool = self._toolMap[job.tool_id];

    //self.info( '\t jobData:', jobData );
    return jobData;
};

/**
 */
JobDAG.prototype._processInputs = function __processInputs(job) {
    var self = this;
    var inputs = job.inputs;
    var inputMap = {};
    _.each(inputs, (input, nameInJob) => {
        input = _.clone(self._validateInputOutput(input));
        input.name = nameInJob;
        // since this is a DAG and we're processing in order of create time,
        //  the inputs for this job will already be listed in _outputIdToJobMap
        //  TODO: we can possibly exploit this
        //console.debug( 'input in _outputIdToJobMap', self._outputIdToJobMap[ input.id ] );
        input.content = self._historyContentsMap[input.id];
        inputMap[input.id] = input;
    });
    return inputMap;
};

/**
 */
JobDAG.prototype._validateInputOutput = function __validateInputOutput(inputOutput) {
    if (!inputOutput.id) {
        throw new Error("No id on job input/output: ", JSON.stringify(inputOutput));
    }
    if (!inputOutput.src || inputOutput.src !== "hda") {
        throw new Error("Bad src on job input/output: ", JSON.stringify(inputOutput));
    }
    return inputOutput;
};

/**
 */
JobDAG.prototype._processOutputs = function __processOutputs(job) {
    var self = this;
    var outputs = job.outputs;
    var outputMap = {};
    _.each(outputs, (output, nameInJob) => {
        output = _.clone(self._validateInputOutput(output));
        output.name = nameInJob;
        // add dataset content to jobData
        output.content = self._historyContentsMap[output.id];
        outputMap[output.id] = output;

        self._outputIdToJobMap[output.id] = job.id;
    });
    return outputMap;
};

/**  */
JobDAG.prototype._filterJobs = function __filterJobs() {
    var self = this;
    return self._jobsData.filter((j, i) => self._filterJob(j, i));
};

/**
 */
JobDAG.prototype._filterJob = function _filterJob(jobData, index) {
    // apply filters after processing job allowing access to the additional data above inside the filters
    var self = this;
    for (var i = 0; i < self.filters.length; i++) {
        if (!self.filters[i].call(self, jobData)) {
            self.debug("\t job", jobData.job.id, " has been filtered out by function:\n", self.filters[i]);
            return false;
        }
    }
    return true;
};

/** Walk all the jobs (vertices), attempting to find connections
 *  between datasets used as both inputs and outputs (edges)
 */
JobDAG.prototype.createGraph = function _createGraph(jobsData) {
    var self = this;
    self.debug("connections:");
    //console.debug( jobsData );

    _.each(jobsData, jobData => {
        var id = jobData.job.id;
        self.debug("\t", id, jobData);
        self.createVertex(id, jobData);
    });
    _.each(jobsData, jobData => {
        var targetId = jobData.job.id;
        _.each(jobData.inputs, (input, inputId) => {
            //console.debug( '\t\t target input:', inputId, input );
            var sourceId = self._outputIdToJobMap[inputId];
            //console.debug( '\t\t source job id:', sourceId );
            if (!sourceId) {
                var joblessVertex = self.createJobLessVertex(inputId);
                sourceId = joblessVertex.name;
            }
            //TODO:?? no checking here whether sourceId is actually in the vertex map
            //console.debug( '\t\t creating edge, source:', sourceId, self.vertices[ sourceId ] );
            //console.debug( '\t\t creating edge, target:', targetId, self.vertices[ targetId ] );
            self.createEdge(sourceId, targetId, self.directed, {
                dataset: inputId
            });
        });
    });
    //console.debug( self.toVerticesAndEdges().edges );

    self.debug("final graph: ", JSON.stringify(self.toVerticesAndEdges(), null, "  "));
    return self;
};

/** Return a 'mangled' version of history contents id to prevent contents <-> job id collision */
JobDAG.prototype.createJobLessVertex = function _createJobLessVertex(contentId) {
    // currently, copied contents are the only history contents without jobs (that I know of)
    //note: following needed to prevent id collision btwn content and jobs in vertex map
    var JOBLESS_ID_MANGLER = "copy-";

    var mangledId = JOBLESS_ID_MANGLER + contentId;
    return this.createVertex(mangledId, this._historyContentsMap[contentId]);
};

/** Override to re-sort (ugh) jobs in each component by update time */
JobDAG.prototype.weakComponentGraphArray = function() {
    var dag = this;
    return this.weakComponents().map(component => {
        //TODO: this seems to belong above (in sort) - why isn't it preserved?
        // note: using create_time (as opposed to update_time)
        //  since update_time for jobless/copied datasets is changes more often
        component.vertices.sort(function cmpCreate(a, b) {
            var aCreateTime = a.data.job ? a.data.job.create_time : a.data.create_time;

            var bCreateTime = b.data.job ? b.data.job.create_time : b.data.create_time;

            if (aCreateTime > bCreateTime) {
                return 1;
            }
            if (aCreateTime < bCreateTime) {
                return -1;
            }
            return 0;
        });
        return new GRAPH.Graph(dag.directed, component);
    });
};

JobDAG.prototype._jobsDataMap = function() {
    var jobsDataMap = {};
    this._jobsData.forEach(jobData => {
        jobsDataMap[jobData.job.id] = jobData;
    });
    return jobsDataMap;
};

// ============================================================================
export default JobDAG;
