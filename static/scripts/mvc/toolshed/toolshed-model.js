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
        urlRoot: Galaxy.root + "api/tool_shed_repositories/shed_categories"
    }), ToolShedCategoriesCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed_repositories/shed_categories",
        model: ToolShedCategoriesModel
    }), ToolShedCategoryModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed_repositories/shed_category"
    }), ToolShedCategoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed_repositories/shed_category",
        model: ToolShedCategoryModel
    }), ToolShedRepositoryModel = Backbone.Model.extend({
        defaults: [ {} ],
        urlRoot: Galaxy.root + "api/tool_shed_repositories/shed_repository"
    }), ToolShedRepositoryCollection = Backbone.Collection.extend({
        url: Galaxy.root + "api/tool_shed_repositories/shed_repository",
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