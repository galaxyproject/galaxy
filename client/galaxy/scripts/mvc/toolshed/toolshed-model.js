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
        urlRoot: Galaxy.root + 'api/tool_shed_repositories/shed_categories',
    });

    var ToolShedCategoriesCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed_repositories/shed_categories',
        model: ToolShedCategoriesModel
    });

    var ToolShedCategoryModel = Backbone.Model.extend({
        defaults: [{}],
        urlRoot: Galaxy.root + 'api/tool_shed_repositories/shed_category',
    });

    var ToolShedCategoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed_repositories/shed_category',
        model: ToolShedCategoryModel
    });

    var ToolShedRepositoryModel = Backbone.Model.extend({
        defaults: [{}],
        urlRoot: Galaxy.root + 'api/tool_shed_repositories/shed_repository',
    });

    var ToolShedRepositoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + 'api/tool_shed_repositories/shed_repository',
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
