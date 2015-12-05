define([
    'utils/utils',
    'layout/menu',
    'layout/scratchbook',
    'mvc/user/user-quotameter',
], function(Utils, Menu, Scratchbook, QuotaMeter) {

/** Masthead **/
var GalaxyMasthead = Backbone.View.extend({
    // base element
    el_masthead: '#everything',

    // options
    options : null,

    // background
    $background: null,

    // list
    list: [],

    // initialize
    initialize : function(options) {
        // update options
        this.options = options;

        // HACK: due to body events defined in panel.js
        $("body").off();

        // define this element
        this.setElement($(this._template(options)));
        // add to page
        $( '#masthead' ).replaceWith( this.$el );

        // assign background
        this.$background = $(this.el).find('#masthead-background');

        // loop through beforeunload functions if the user attempts to unload the page
        var self = this;
        $(window).on('click', function( e ) {
            var $download_link = $( e.target ).closest( 'a[download]' );
            if ( $download_link.length == 1 ) {
                if( $( 'iframe[id=download]' ).length === 0 ){
                    $( 'body' ).append( $( '<iframe id="download" style="display: none;" />' ) );
                }
                $( 'iframe[id=download]' ).attr( 'src', $download_link.attr( 'href' ) );
                e.preventDefault();
            }
        }).on('beforeunload', function() {
            var text = "";
            for (var key in self.list) {
                if (self.list[key].options.onbeforeunload) {
                    var q = self.list[key].options.onbeforeunload();
                    if (q) text += q + " ";
                }
            }
            if (text !== "") {
                return text;
            }
        });

        // construct default menu options
        this.menu = Galaxy.menu = new Menu.GalaxyMenu({
            masthead    : this,
            config      : this.options
        });

        // scratchpad
        this.frame = Galaxy.frame = new Scratchbook.GalaxyFrame({
            masthead    : this,
        });

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        this.quotaMeter = Galaxy.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model       : Galaxy.user,
            el          : this.$( '.quota-meter-container' )
        }).render();
    },

    // configure events
    events: {
        'click'     : '_click',
        'mousedown' : function(e) { e.preventDefault() }
    },

    // adds a new item to the masthead
    append : function(item) {
        return this._add(item, true);
    },

    // adds a new item to the masthead
    prepend : function(item) {
        return this._add(item, false);
    },

    // activate
    highlight: function(id) {
        var current = $(this.el).find('#' + id + '> li');
        if (current) {
            current.addClass('active');
        }
    },

    // adds a new item to the masthead
    _add : function(item, append) {
        var $loc = $(this.el).find('#' + item.location);
        if ($loc){
            // create frame for new item
            var $current = $(item.el);

            // configure class in order to mark new items
            $current.addClass('masthead-item');

            // append to masthead
            if (append) {
                $loc.append($current);
            } else {
                $loc.prepend($current);
            }

            // add to list
            this.list.push(item);
        }

        // location not found
        return null;
    },

    // handle click event
    _click: function(e) {
        // close all popups
        var $all = $(this.el).find('.popup');
        if ($all) {
            $all.hide();
        }

        // open current item
        var $current = $(e.target).closest('.masthead-item').find('.popup');
        if ($(e.target).hasClass('head')) {
            $current.show();
            this.$background.show();
        } else {
            this.$background.hide();
        }
    },

    /*
        HTML TEMPLATES
    */

    // fill template
    _template: function(options) {
        var brand_text = options.brand ? ("/ " + options.brand) : "" ;
        return  '<div><div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' +
                    '<div style="position: relative; right: -50%; float: left;">' +
                        '<div id="navbar" style="display: block; position: relative; right: 50%;"></div>' +
                    '</div>' +
                   '<div class="navbar-brand">' +
                        '<a href="' + options.logo_url + '">' +
                            '<img style="margin-left: 0.35em;" border="0" src="' + Galaxy.root + 'static/images/galaxyIcon_noText.png">' +
                            '<span id="brand"> Galaxy ' + brand_text + '</span>' +
                        '</a>' +
                    '</div>' +
                    '<div class="quota-meter-container"></div>' +
                    '<div id="iconbar" class="iconbar"></div>' +
                '</div>' +
                '<div id="masthead-background" style="display: none; position: absolute; top: 33px; width: 100%; height: 100%; z-index: 1010"></div>' +
                '</div>';
    }
});

// return
return {
    GalaxyMasthead: GalaxyMasthead
};

});
