define([], function() {
    var searchShed = function(request, response) {
        var that = this;
        var shed_url = this.shed_url;
        var base_url = Galaxy.root + 'api/tool_shed/search';
        $.get(base_url, {term: request.term, tool_shed_url: shed_url}, function(data) {
            result_list = that.shedParser(data);
            response(result_list);
        });

    };

    var shedParser = function(jsondata) {
        var results = [];
        var hits = jsondata.hits;
        $.each(hits, function(hit) {
            var record = hits[hit];
            var label = record.repository.name + ' by ' + record.repository.repo_owner_username + ': ' + record.repository.description;
            result = {value: record.repository.id, label: label};
            results.push(result);
        });
        return results;
    };

    var queueKey = function(repository_metadata) {
        if (repository_metadata.tool_shed_url === undefined) {
            repository_metadata.tool_shed_url = $("#repository_details").attr('data-shedurl');
        }
        // Make sure there is never a trailing slash on the shed URL.
        if (repository_metadata.tool_shed_url.substr(-1) == '/') {
            repository_metadata.tool_shed_url = repository_metadata.tool_shed_url.substr(0, repository_metadata.tool_shed_url.length - 1);
        }
        return repository_metadata.tool_shed_url + '|' + repository_metadata.repository_id + '|' + repository_metadata.changeset_revision;
    }

    return {searchShed: searchShed, shedParser: shedParser, queueKey: queueKey};
});
