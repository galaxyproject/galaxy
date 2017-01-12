define([], function() {
    var loadRepo = function(a,b,c,d) {
        console.log(a);
        console.log(b);
        console.log(c);
        console.log(d);
    };

    var searchShed = function(request, response) {
        var that = this;
        console.log('shed_url');
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
            console.log(record);
            result = {value: record.repository.id, label: label};
            console.log(result);
            results.push(result);
        });
        return results;
    };

    return {loadRepo: loadRepo, searchShed: searchShed, shedParser: shedParser};
});
