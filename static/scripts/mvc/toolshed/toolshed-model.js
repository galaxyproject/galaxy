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
    });
    return {
        ShedModel: ToolShedModel,
        ShedsCollection: ToolShedsCollection,
        Category: ToolShedCategoriesModel,
        Categories: ToolShedCategoriesCollection,
        CategoryModel: ToolShedCategoryModel,
        CategoryCollection: ToolShedCategoryCollection,
        RepositoryModel: ToolShedRepositoryModel,
        RepositoryCollection: ToolShedRepositoryCollection
    };
});