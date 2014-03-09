({
    baseUrl : "../../../../../static/scripts/",
    paths   : {
        "plugin": "../../config/plugins/visualizations/charts/static"
    },
    shim    : {
        "libs/underscore": { exports: "_" },
        "libs/backbone/backbone": { exports: "Backbone" }
    },
    name    : "plugin/app",
    out     : "../static/build-app.js",
})