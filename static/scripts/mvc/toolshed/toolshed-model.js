define([], function() {
    var ToolShedModel = Backbone.Model.extend({
        defaults: {
            url: "https://toolshed.g2.bx.psu.edu/",
            name: "Galaxy Main Tool Shed"
        },
        urlRoot: Galaxy.root + "api/tool_shed"
    }), ToolShedsCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed",
        model: ToolShedModel
    }), ToolShedCategoriesModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed/contents"
    }), ToolShedCategoriesCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed/contents",
        model: ToolShedCategoriesModel
    }), ToolShedCategoryModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed/category"
    }), ToolShedCategoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed/category",
        model: ToolShedCategoryModel
    }), ToolShedRepositoryModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed/repository"
    }), ToolShedRepositoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed/repository",
        model: ToolShedRepositoryModel
    }), RepoQueueModel = Backbone.Model.extend({
        url: "#"
    }), RepoQueueCollection = Backbone.Collection.extend({
        url: "#",
        model: RepoQueueModel,
        fetch: function() {
            var collection = this, repositories = Array(), repositories_enc = JSON.parse(localStorage.repositories), queue_keys = Object.keys(repositories_enc);
            return _.each(queue_keys, function(key) {
                var repo = repositories_enc[key];
                repo.queue_key = key, repositories.push(repo);
            }), console.log({
                collection: repositories
            }), collection.reset(repositories), Backbone.Collection.prototype.fetch.call(this);
        }
    }), RepoStatusModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed/status"
    }), RepoStatusCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed/status",
        model: RepoStatusModel
    });
    return {
        ShedModel: ToolShedModel,
        ShedsCollection: ToolShedsCollection,
        Category: ToolShedCategoriesModel,
        Categories: ToolShedCategoriesCollection,
        CategoryModel: ToolShedCategoryModel,
        CategoryCollection: ToolShedCategoryCollection,
        RepositoryModel: ToolShedRepositoryModel,
        RepositoryCollection: ToolShedRepositoryCollection,
        RepoQueue: RepoQueueCollection,
        RepoStatus: RepoStatusCollection
    };
});