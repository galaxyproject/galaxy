define( [], function() {

/**
 * -- Routers --
 */

/**
 * Router for library browser.
 */
var LibraryRouter = Backbone.Router.extend({    
    routes: {
        "" :                 "libraries",
        "folders/:id" :      "folder_content"
    }
});

return {
    LibraryRouter: LibraryRouter,
};

})