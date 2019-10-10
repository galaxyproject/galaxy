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
    //this.logger = console;

    this.filters = [];

    // instance vars
    //TODO: needed?
    this._jobsData = [];
    this._historyContentsMap = {};
    this._toolMap = {};

    this._outputIdToJobMap = {};
    this.noInputJobs = [];
    this.noOutputJobs = [];

    //TODO: save these?
    this.filteredSetMetadata = [];
    this.filteredErroredJobs = [];

    this.dataKeys = ["jobs", "historyContents", "tools"];
    _super.call(this, true, _.pick(options, this.dataKeys), _.omit(options, this.dataKeys));
};
JobDAG.prototype = new GRAPH.Graph();
JobDAG.prototype.constructor = JobDAG;

// add logging ability - turn off/on using the this.logger statement above
addLogging(JobDAG);

// ----------------------------------------------------------------------------
/** process jobs, options, filters, and any history data, then create the graph */
JobDAG.prototype.init = function _init(options) {
    options = options || {};

    this.options = _.defaults(options, {
        excludeSetMetadata: false
    });
    this.filters = this._initFilters();

    _super.prototype.init.call(this, options);
    return this;
};

/** add job filters based on options */
JobDAG.prototype._initFilters = function __initFilters() {
    var filters = [];

    if (this.options.excludeSetMetadata) {
        this.filteredSetMetadata = [];
        filters.push(function filterSetMetadata(jobData) {
            if (jobData.job.tool_id !== "__SET_METADATA__") {
                return true;
            }
            this.filteredSetMetadata.push(jobData.job.id);
            return false;
        });
    }

    if (this.options.excludeErroredJobs) {
        this.filteredErroredJobs = [];
        filters.push(function filterErrored(jobData) {
            if (jobData.job.state !== "error") {
                return true;
            }
            this.filteredErroredJobs.push(jobData.job.id);
            return false;
        });
    }

    // all outputs deleted
    // all outputs hidden

    if (_.isArray(this.options.filters)) {
        filters = filters.concat(this.options.filters);
    }
    this.debug("filters len:", filters.length);
    return filters;
};

/**  */
JobDAG.prototype.read = function _read(data) {
    if (_.has(data, "historyContents") && _.has(data, "jobs") && _.has(data, "tools")) {
        // a job dag is composed of these three elements:
        //  clone the 3 data sources into the DAG, processing the jobs finally using the history and tools
        this.preprocessHistoryContents(data.historyContents || [])
            .preprocessTools(data.tools || {})
            .preprocessJobs(data.jobs || []);

        // filter jobs and create the vertices and edges of the job DAG
        this.createGraph(this._filterJobs());
        return this;
    }
    return _super.prototype.read.call(this, data);
};

/**  */
JobDAG.prototype.preprocessHistoryContents = function _preprocessHistoryContents(historyContents) {
    this.info("processing history");
    this._historyContentsMap = {};

    historyContents.forEach((content, i) => {
        this._historyContentsMap[content.id] = _.clone(content);
    });
    return this;
};

/**  */
JobDAG.prototype.preprocessTools = function _preprocessTools(tools) {
    this.info("processing tools");
    this._toolMap = {};

    _.each(tools, (tool, id) => {
        this._toolMap[id] = _.clone(tool);
    });
    return this;
};

/** sort the cloned jobs, decorate with tool and history contents info, and store in prop array */
JobDAG.prototype.preprocessJobs = function _preprocessJobs(jobs) {
    this.info("processing jobs");
    this._outputIdToJobMap = {};

    this._jobsData = this.sort(jobs).map(job => this.preprocessJob(_.clone(job)));

    return this;
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

    var jobData = { job: job };

    jobData.inputs = this._processInputs(job);
    if (_.size(jobData.inputs) === 0) {
        this.noInputJobs.push(job.id);
    }
    jobData.outputs = this._processOutputs(job);
    if (_.size(jobData.outputs) === 0) {
        this.noOutputJobs.push(job.id);
    }

    jobData.tool = this._toolMap[job.tool_id];

    //this.info( '\t jobData:', jobData );
    return jobData;
};

/**
 */
JobDAG.prototype._processInputs = function __processInputs(job) {
    var inputs = job.inputs;
    var inputMap = {};
    _.each(inputs, (input, nameInJob) => {
        input = _.clone(this._validateInputOutput(input));
        input.name = nameInJob;
        // since this is a DAG and we're processing in order of create time,
        //  the inputs for this job will already be listed in _outputIdToJobMap
        //  TODO: we can possibly exploit this
        input.content = this._historyContentsMap[input.id];
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
    var outputs = job.outputs;
    var outputMap = {};
    _.each(outputs, (output, nameInJob) => {
        output = _.clone(this._validateInputOutput(output));
        output.name = nameInJob;
        // add dataset content to jobData
        output.content = this._historyContentsMap[output.id];
        outputMap[output.id] = output;

        this._outputIdToJobMap[output.id] = job.id;
    });
    return outputMap;
};

/**  */
JobDAG.prototype._filterJobs = function __filterJobs() {
    return this._jobsData.filter((j, i) => this._filterJob(j, i));
};

/**
 */
JobDAG.prototype._filterJob = function _filterJob(jobData, index) {
    // apply filters after processing job allowing access to the additional data above inside the filters
    for (var i = 0; i < this.filters.length; i++) {
        if (!this.filters[i].call(this, jobData)) {
            this.debug("\t job", jobData.job.id, " has been filtered out by function:\n", this.filters[i]);
            return false;
        }
    }
    return true;
};

/** Walk all the jobs (vertices), attempting to find connections
 *  between datasets used as both inputs and outputs (edges)
 */
JobDAG.prototype.createGraph = function _createGraph(jobsData) {
    this.debug("connections:");

    _.each(jobsData, jobData => {
        var id = jobData.job.id;
        this.debug("\t", id, jobData);
        this.createVertex(id, jobData);
    });
    _.each(jobsData, jobData => {
        var targetId = jobData.job.id;
        _.each(jobData.inputs, (input, inputId) => {
            var sourceId = this._outputIdToJobMap[inputId];
            if (!sourceId) {
                var joblessVertex = this.createJobLessVertex(inputId);
                sourceId = joblessVertex.name;
            }
            //TODO:?? no checking here whether sourceId is actually in the vertex map
            this.createEdge(sourceId, targetId, this.directed, {
                dataset: inputId
            });
        });
    });

    this.debug("final graph: ", JSON.stringify(this.toVerticesAndEdges(), null, "  "));
    return this;
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
