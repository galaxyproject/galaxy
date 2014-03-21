// dependencies
define(['plugin/models/chart'], function(Chart) {

// collection
return Backbone.Collection.extend(
{
    model: Chart,
    
    // save charts
    save: function() {
        // create visualization
        var vis = new Visualization({
            type    : 'charts',
            config  : {
                charts : []
            }
        });
        
        // copy attributes
        //vis.set(this.attributes);
        
        // save visualization
        vis.save()
            .fail( function( xhr, status, message ){
                console.error( xhr, status, message );
                alert( 'Error loading data:\n' + xhr.responseText );
            });
    }
});

});