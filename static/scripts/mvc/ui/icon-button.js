define([
    //jquery
    //backbone
], function(){
//=============================================================================
/**
 * backbone model for icon buttons
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title           : "",
        icon_class      : "",
        on_click        : null,
        menu_options    : null,
        is_menu_button  : true,
        id              : null,
        href            : null,
        target          : null,
        enabled         : true,
        visible         : true,
        tooltip_config  : {}
    }
});

/**
 *  backbone view for icon buttons
 */
var IconButtonView = Backbone.View.extend({

    initialize : function(){
        // better rendering this way
        this.model.attributes.tooltip_config = { placement : 'bottom' };
        this.model.bind( 'change', this.render, this );
    },

    render : function( ){
        // hide tooltip
        this.$el.tooltip( 'hide' );

        var new_elem = this.template( this.model.toJSON() );
        // configure tooltip
        new_elem.tooltip( this.model.get( 'tooltip_config' ));
        this.$el.replaceWith( new_elem );
        this.setElement( new_elem );
        return this;
    },

    events : {
        'click' : 'click'
    },

    click : function( event ){
        // if on_click pass to that function
        if( _.isFunction( this.model.get( 'on_click' ) ) ){
            this.model.get( 'on_click' )( event );
            return false;
        }
        // otherwise, bubble up ( to href or whatever )
        return true;
    },

    // generate html element
    template: function( options ){
        var buffer = 'title="' + options.title + '" class="icon-button';

        if( options.is_menu_button ){
            buffer += ' menu-button';
        }

        buffer += ' ' + options.icon_class;

        if( !options.enabled ){
            buffer += '_disabled';
        }

        // close class tag
        buffer += '"';

        if( options.id ){
            buffer += ' id="' + options.id + '"';
        }

        buffer += ' href="' + options.href + '"';
        // add target for href
        if( options.target ){
            buffer += ' target="' + options.target + '"';
        }
        // set visibility
        if( !options.visible ){
            buffer += ' style="display: none;"';
        }

        // enabled/disabled
        if ( options.enabled ){
            buffer = '<a ' + buffer + '/>';
        } else {
            buffer = '<span ' + buffer + '/>';
        }

        // return element
        return $( buffer );
    }
} );

// define collection
var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});

/**
 * menu with multiple icon buttons
 * views are not needed nor used for individual buttons
 */
var IconButtonMenuView = Backbone.View.extend({

    tagName: 'div',

    initialize: function(){
        this.render();
    },

    render: function(){
        // initialize icon buttons
        var self = this;
        this.collection.each(function(button){
            // create and add icon button to menu
            var elt = $('<a/>')
                .attr('href', 'javascript:void(0)')
                .attr('title', button.attributes.title)
                .addClass('icon-button menu-button')
                .addClass(button.attributes.icon_class)
                .appendTo(self.$el)
                .click(button.attributes.on_click);

            // configure tooltip
            if (button.attributes.tooltip_config){
                elt.tooltip(button.attributes.tooltip_config);
            }

            // add popup menu to icon
            var menu_options = button.get('options');
            if (menu_options){
                make_popupmenu(elt, menu_options);
            }
        });

        // return
        return this;
    }
});

/**
 * Returns an IconButtonMenuView for the provided configuration.
 * Configuration is a list of dictionaries where each dictionary
 * defines an icon button. Each dictionary must have the following
 * elements: icon_class, title, and on_click.
 */
var create_icon_buttons_menu = function(config, global_config)
{
    // initialize global configuration
    if (!global_config) global_config = {};

    // create and initialize menu
    var buttons = new IconButtonCollection(
        _.map(config, function(button_config){
            return new IconButton(_.extend(button_config, global_config));
        })
    );

    // return menu
    return new IconButtonMenuView( {collection: buttons} );
};


//=============================================================================
    return {
        IconButton              : IconButton,
        IconButtonView          : IconButtonView,
        IconButtonCollection    : IconButtonCollection,
        IconButtonMenuView      : IconButtonMenuView,
        create_icon_buttons_menu: create_icon_buttons_menu
    };
})
