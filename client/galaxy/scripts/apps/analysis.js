
var App = require( '../mvc/app/app-view' );

//TODO: this doesn't address multiple apps per page
window.app = function app( options, bootstrapped ){
    $( function() {
        var app = new App( options.config );
    });
};
