/**
 *  Visualization selection grid
 */
import Utils from "utils/utils";
import Thumbnails from "mvc/ui/ui-thumbnails";
import Portlet from "mvc/ui/ui-portlet";
import Ui from "mvc/ui/ui-misc";
var View = Backbone.View.extend({
    initialize: function( options ) {
        var self = this;
        this.setElement( $( '<div/>' ) );
        this.model = new Backbone.Model();
        $.ajax({
            url: `${Galaxy.root}api/datasets/${options.dataset_id}`
        })
        .done(dataset => {
            if ( dataset.visualizations.length === 0 ) {
                self.$el.append( $( '<div/>' ).addClass( 'errormessagelarge' )
                        .append( $( '<p/>' ).text( 'Unfortunately we could not identify a suitable plugin. Feel free to contact us if you are aware of visualizations for this datatype.' )  ) );
            } else {
                self.model.set( { 'dataset': dataset } );
                self.render();
            }
        });
    },

    render: function() {
        var self = this;
        var dataset = this.model.get( 'dataset' );
        this.vis_index = {};
        this.vis_array = [];
        _.each( dataset.visualizations, function( v, id ) {
            var dict = {
                id              : id,
                name            : v.name,
                keywords        : v.keywords || [],
                title           : v.html,
                image_src       : v.logo ? Galaxy.root + v.logo : null,
                description     : v.description || 'No description available.',
                regular         : v.regular,
                visualization   : v
            }
            self.vis_index[ dict.id ] = dict;
            self.vis_array.push( dict );
        });
        this.types = new Thumbnails.View({
            title_default   : 'Suggested plugins',
            title_list      : 'List of available plugins',
            collection      : this.vis_array,
            ondblclick      : function( id ) {
                var vis_type = self.vis_index[ id ];
                $('#galaxy_main').attr('src', vis_type.visualization.href);
            }
        });
        this.$el.empty().append( this.types.$el );
    }
});
export default { View: View }