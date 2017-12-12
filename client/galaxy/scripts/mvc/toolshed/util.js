var searchShed = function(request, response) {
    var that = this;
    var shed_url = this.shed_url;
    var base_url = `${Galaxy.root}api/tool_shed/search`;
    $.get(base_url, { term: request.term, tool_shed_url: shed_url }, data => {
        var result_list = that.shedParser(data);
        response(result_list);
    });
};

var shedParser = jsondata => {
    var results = [];
    var hits = jsondata.hits;
    $.each(hits, hit => {
        var record = hits[hit];
        var label = `${record.repository.name} by ${record.repository.repo_owner_username}: ${
            record.repository.description
        }`;
        var result = { value: record.repository.id, label: label };
        results.push(result);
    });
    return results;
};

var addToQueue = metadata => {
    if (metadata.tool_shed_url.substr(-1) == "/") {
        metadata.tool_shed_url = metadata.tool_shed_url.substr(0, metadata.tool_shed_url.length - 1);
    }
    var key = `${metadata.tool_shed_url}|${metadata.repository_id}|${metadata.changeset_revision}`;
    var queued_repos = new Object();
    if (localStorage.repositories) {
        queued_repos = JSON.parse(localStorage.repositories);
    }
    queued_repos[key] = metadata;
    localStorage.repositories = JSON.stringify(queued_repos);
};

var queueLength = () => {
    if (localStorage.hasOwnProperty("repositories")) {
        var repo_queue = JSON.parse(localStorage.repositories);
        var queue_length = Object.keys(repo_queue).length;
        return queue_length;
    } else {
        return 0;
    }
};

export default {
    searchShed: searchShed,
    shedParser: shedParser,
    addToQueue: addToQueue,
    queueLength: queueLength
};
