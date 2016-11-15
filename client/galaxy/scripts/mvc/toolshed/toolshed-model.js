define([], function() {

    var ToolShedModel = Backbone.Model.extend({
        defaults: {"url": "https://toolshed.g2.bx.psu.edu/", "name": "Galaxy Main Tool Shed"},
        urlRoot: Galaxy.root + 'api/tool_shed',
    });

    var ToolShedsCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed',
        model: ToolShedModel
    });

    var ToolShedCategoriesModel = Backbone.Model.extend({
        defaults: [{}],
        urlRoot: Galaxy.root + 'api/tool_shed/contents',
    });

    var ToolShedCategoriesCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed/contents',
        model: ToolShedCategoriesModel
    });

    var ToolShedCategoryModel = Backbone.Model.extend({
        defaults: [{}],
        urlRoot: Galaxy.root + 'api/tool_shed/category',
    });

    var ToolShedCategoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed/category',
        model: ToolShedCategoryModel
    });

    var ToolShedRepositoryModel = Backbone.Model.extend({
        defaults: [{}],
        urlRoot: Galaxy.root + 'api/tool_shed/repository',
    });

    var ToolShedRepositoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed/repository',
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
