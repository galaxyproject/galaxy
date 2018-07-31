import * as Backbone from "backbone";
import * as _ from "underscore";

/* global Galaxy */

var ToolShedModel = Backbone.Model.extend({
    defaults: {
        url: "https://toolshed.g2.bx.psu.edu/",
        name: "Galaxy Main Tool Shed"
    },
    urlRoot: `${Galaxy.root}api/tool_shed`
});

var ToolShedsCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/tool_shed`,
    model: ToolShedModel
});

var ToolShedCategoriesModel = Backbone.Model.extend({
    defaults: [{}],
    urlRoot: `${Galaxy.root}api/tool_shed/contents`
});

var ToolShedCategoriesCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/tool_shed/contents`,
    model: ToolShedCategoriesModel
});

var ToolShedCategoryModel = Backbone.Model.extend({
    defaults: [{}],
    urlRoot: `${Galaxy.root}api/tool_shed/category`
});

var ToolShedCategoryCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/tool_shed/category`,
    model: ToolShedCategoryModel
});

var ToolShedRepositoryModel = Backbone.Model.extend({
    defaults: [{}],
    urlRoot: `${Galaxy.root}api/tool_shed/repository`
});

var ToolShedRepositoryCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/tool_shed/repository`,
    model: ToolShedRepositoryModel
});

var RepoQueueModel = Backbone.Model.extend({
    url: "#"
});

var RepoQueueCollection = Backbone.Collection.extend({
    url: "#",
    model: RepoQueueModel,
    fetch: function() {
        var repositories = Array();
        var repositories_enc;
        if (window.localStorage.hasOwnProperty("repositories")) {
            repositories_enc = JSON.parse(window.localStorage.repositories);
        } else {
            repositories_enc = [];
        }
        var queue_keys = Object.keys(repositories_enc);
        _.each(queue_keys, key => {
            var repo = repositories_enc[key];
            repo.queue_key = key;
            repositories.push(repo);
        });
        this.reset(repositories);
        return Backbone.Collection.prototype.fetch.call(this);
    }
});

var RepoStatusModel = Backbone.Model.extend({
    defaults: [{}],
    urlRoot: `${Galaxy.root}api/tool_shed/status`
});

var RepoStatusCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/tool_shed/status`,
    model: RepoStatusModel
});

var WorkflowToolsModel = Backbone.Model.extend({
    defaults: [{}],
    urlRoot: `${Galaxy.root}api/workflows?missing_tools=True`
});

var WorkflowToolsCollection = Backbone.Collection.extend({
    url: `${Galaxy.root}api/workflows?missing_tools=True`,
    model: WorkflowToolsModel
});

export default {
    ShedModel: ToolShedModel,
    ShedsCollection: ToolShedsCollection,
    Category: ToolShedCategoriesModel,
    Categories: ToolShedCategoriesCollection,
    CategoryModel: ToolShedCategoryModel,
    CategoryCollection: ToolShedCategoryCollection,
    RepositoryModel: ToolShedRepositoryModel,
    RepositoryCollection: ToolShedRepositoryCollection,
    RepoQueue: RepoQueueCollection,
    RepoStatus: RepoStatusCollection,
    WorkflowTools: WorkflowToolsCollection
};
