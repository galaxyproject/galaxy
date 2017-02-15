define([], function() {
    var searchShed = function(request, response) {
        var that = this, shed_url = this.shed_url, base_url = Galaxy.root + "api/tool_shed/search";
        $.get(base_url, {
            term: request.term,
            tool_shed_url: shed_url
        }, function(data) {
            result_list = that.shedParser(data), response(result_list);
        });
    }, shedParser = function(jsondata) {
        var results = [], hits = jsondata.hits;
        return $.each(hits, function(hit) {
            var record = hits[hit], label = record.repository.name + " by " + record.repository.repo_owner_username + ": " + record.repository.description;
            result = {
                value: record.repository.id,
                label: label
            }, results.push(result);
        }), results;
    };
    return {
        searchShed: searchShed,
        shedParser: shedParser,
        queueKey: queueKey
    };
});