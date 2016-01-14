/** Masthead Collection **/
define(['mvc/tours'], function( Tours ) {
var Collection = Backbone.Collection.extend({
    model: Backbone.Model.extend({
        defaults: {
            visible         : true,
            target          : '_parent'
        }
    }),
    fetch: function( options ){
        options = options || {};
        this.reset();

        //
        // Analyze data tab.
        //
        this.add({
            id              : 'analysis',
            title           : 'Analyze Data',
            url             : '',
            tooltip         : 'Analysis home view'
        });

        //
        // Workflow tab.
        //
        this.add({
            id              : 'workflow',
            title           : 'Workflow',
            url             : 'workflow',
            tooltip         : 'Chain tools into workflows',
            disabled        : !Galaxy.user.id
        });

        //
        // 'Shared Items' or Libraries tab.
        //
        this.add({
            id              : 'shared',
            title           : 'Shared Data',
            url             : 'library/index',
            tooltip         : 'Access published resources',
            menu            : [{
                    title   : 'Data Libraries deprecated',
                    url     : 'library/index'
                },{
                    title   : 'Data Libraries',
                    url     : 'library/list',
                    divider : true
                },{
                    title   : 'Published Histories',
                    url     : 'history/list_published'
                },{
                    title   : 'Published Workflows',
                    url     : 'workflow/list_published'
                },{
                    title   : 'Published Visualizations',
                    url     : 'visualization/list_published'
                },{
                    title   : 'Published Pages',
                    url     : 'page/list_published'
            }]
        });

        //
        // Lab menu.
        //
        options.user_requests && this.add({
            id              : 'lab',
            title           : 'Lab',
            menu            : [{
                    title   : 'Sequencing Requests',
                    url     : 'requests/index'
                },{
                    title   : 'Find Samples',
                    url     : 'requests/find_samples_index'
                },{
                    title   : 'Help',
                    url     : options.lims_doc_url
            }]
        });

        //
        // Visualization tab.
        //
        this.add({
            id              : 'visualization',
            title           : 'Visualization',
            url             : 'visualization/list',
            tooltip         : 'Visualize datasets',
            disabled        : !Galaxy.user.id,
            menu            : [{
                    title   : 'New Track Browser',
                    url     : 'visualization/trackster',
                    target  : '_frame'
                },{
                    title   : 'Saved Visualizations',
                    url     : 'visualization/list',
                    target  : '_frame'
            }]
        });

        //
        // Admin.
        //
        Galaxy.user.get( 'is_admin' ) && this.add({
            id              : 'admin',
            title           : 'Admin',
            url             : 'admin',
            tooltip         : 'Administer this Galaxy',
            cls             : 'admin-only'
        });

        //
        // Help tab.
        //
        var helpTab = {
            id              : 'help',
            title           : 'Help',
            tooltip         : 'Support, contact, and community hubs',
            menu            : [{
                    title   : 'Support',
                    url     : options.support_url,
                    target  : '_blank'
                },{
                    title   : 'Search',
                    url     : options.search_url,
                    target  : '_blank'
                },{
                    title   : 'Mailing Lists',
                    url     : options.mailing_lists,
                    target  : '_blank'
                },{
                    title   : 'Videos',
                    url     : options.screencasts_url,
                    target  : '_blank'
                },{
                    title   : 'Wiki',
                    url     : options.wiki_url,
                    target  : '_blank'
                },{
                    title   : 'How to Cite Galaxy',
                    url     : options.citation_url,
                    target  : '_blank'
                },{
                    title   : 'Interactive Tours',
                    onclick : function(c){
                        Galaxy.app.display(new Tours.ToursView());
                    },
                    target  : 'galaxy_main'
            }]
        };
        options.terms_url && helpTab.menu.push({
            title   : 'Terms and Conditions',
            url     : options.terms_url,
            target  : '_blank'
        });
        options.biostar_url && helpTab.menu.unshift({
            title   : 'Ask a question',
            url     : 'biostar/biostar_question_redirect',
            target  : '_blank'
        });
        options.biostar_url && helpTab.menu.unshift({
            title   : 'Galaxy Biostar',
            url     : options.biostar_url_redirect,
            target  : '_blank'
        });
        this.add( helpTab );

        //
        // User tab.
        //
        if ( !Galaxy.user.id ){
            var userTab = {
                id              : 'user',
                title           : 'User',
                cls             : 'loggedout-only',
                tooltip         : 'Account registration or login',
                menu            : [{
                    title       : 'Login',
                    url         : 'user/login',
                    target      : 'galaxy_main'
                }]
            };
            options.allow_user_creation && userTab.menu.push({
                title   : 'Register',
                url     : 'user/create',
                target  : 'galaxy_main'
            });
            this.add( userTab );
        } else {
            var userTab = {
                id              : 'user',
                title           : 'User',
                cls             : 'loggedin-only',
                tooltip         : 'Account preferences and saved data',
                menu            : [{
                        title   : 'Logged in as ' + Galaxy.user.get( 'email' )
                    },{
                        title   : 'Preferences',
                        url     : 'user?cntrller=user',
                        target  : 'galaxy_main'
                    },{
                        title   : 'Custom Builds',
                        url     : 'user/dbkeys',
                        target  : 'galaxy_main'
                    },{
                        title   : 'Logout',
                        url     : 'user/logout',
                        target  : '_top',
                        divider : true
                    },{
                        title   : 'Saved Histories',
                        url     : 'history/list',
                        target  : 'galaxy_main'
                    },{
                        title   : 'Saved Datasets',
                        url     : 'dataset/list',
                        target  : 'galaxy_main'
                    },{
                        title   : 'Saved Pages',
                        url     : 'page/list',
                        target  : '_top'
                    },{
                        title   : 'API Keys',
                        url     : 'user/api_keys?cntrller=user',
                        target  : 'galaxy_main'
                }]
            };
            options.use_remote_user && userTab.menu.push({
                title   : 'Public Name',
                url     : 'user/edit_username?cntrller=user',
                target  : 'galaxy_main'
            });
            this.add( userTab );
        }
        var activeView = this.get( options.active_view );
        activeView && activeView.set( 'active', true );
        return new jQuery.Deferred().resolve().promise();
    }
});

/** Masthead tab **/
var Tab = Backbone.View.extend({
    initialize: function ( options ) {
        var self = this;
        this.setElement( this._template() );
        this.$dropdown  = this.$( '.dropdown' );
        this.$toggle    = this.$( '.dropdown-toggle' );
        this.$menu      = this.$( '.dropdown-menu' );
        this.$note      = this.$( '.dropdown-note' );
        this.model = options.model;
        this.$el.attr( 'id', this.model.id );
        this.model.on( 'init change:title', function() {
            this.get( 'title' ) && self.$toggle.html( this.get( 'title' ) );
        }).on( 'init change:visible', function() {
            self.$el.css( { visibility : this.get( 'visible' ) && 'visible' || 'hidden' } );
        }).on( 'init change:note', function() {
            self.$note.html( this.get( 'note' ) );
        }).on( 'init change:note_cls', function() {
            this._prevNoteCls && self.$note.removeClass( this._prevNoteCls );
            this.get( 'note_cls' ) && self.$note.addClass( this._prevNoteCls = this.get( 'note_cls' ) );
        }).on( 'init change:show_note', function() {
            self.$note.css( { 'display' : this.get( 'show_note' ) && 'block' || 'none' } );
        }).on( 'init change:target', function() {
            self.$toggle.attr( 'target', this.get( 'target' ) );
        }).on( 'init change:url', function() {
            this.set( 'url', self._formatUrl( this.get( 'url' ) ) );
            self.$toggle.attr( 'href', this.get( 'url' ) );
        }).on( 'init change:tooltip', function() {
            $( '.tooltip' ).remove();
            self.$toggle.tooltip( 'destroy' ).attr( 'title', this.get( 'tooltip' ) );
            this.get( 'tooltip' ) && self.$toggle.tooltip( { placement: 'bottom' } );
        }).on( 'init change:cls', function() {
            this._prevCls && self.$toggle.removeClass( this._prevCls );
            this.get( 'cls' ) && self.$toggle.addClass( this._prevCls = this.get( 'cls' ) );
        }).on( 'init change:icon', function() {
            this._prevIcon && self.$toggle.removeClass( this._prevIcon );
            this.get( 'icon' ) && self.$toggle.addClass( this._prevIcon = 'fa fa-2x ' + this.get( 'icon' ) );
        }).on( 'init change:toggle', function() {
            self.$toggle[ this.get( 'toggle' ) && 'addClass' || 'removeClass' ]( 'toggle' );
        }).on( 'init change:disabled', function() {
            self.$dropdown[ this.get( 'disabled' ) && 'addClass' || 'removeClass' ]( 'disabled' );
            self._configurePopover();
        }).on( 'init change:active', function() {
            self.$dropdown[ this.get( 'active' ) && 'addClass' || 'removeClass' ]( 'active' );
        }).on( 'init change:show_menu', function() {
            if ( this.get( 'menu' ) && this.get( 'show_menu' ) ) {
                self.$menu.show();
                $( '#dd-helper' ).show().off().on( 'click',  function() {
                    $( '#dd-helper' ).hide();
                    self.model.set( 'show_menu', false );
                });
            } else {
                self.$menu.hide();
                $( '#dd-helper' ).hide();
            }
        }).on( 'init change:menu', function() {
            self.$menu.empty().removeClass( 'dropdown-menu' );
            self.$toggle.find( 'b' ).remove();
            if ( this.get( 'menu' ) ) {
                _.each( this.get( 'menu' ), function( menuItem ) {
                    self.$menu.append( self._buildMenuItem( menuItem ) );
                    menuItem.divider && self.$menu.append( $( '<li/>' ).addClass( 'divider' ) );
                });
                self.$menu.addClass( 'dropdown-menu' );
                self.$toggle.append( $( '<b/>' ).addClass( 'caret' ) );
            }
        }).trigger( 'init' );
    },

    /** Attach events */
    events: {
        'click .dropdown-toggle' : '_toggleClick'
    },

    /** Add new menu item */
    _buildMenuItem: function ( options ) {
        var self = this;
        options = _.defaults( options || {}, {
            title       : '',
            url         : '',
            target      : '_parent'
        });
        options.url = self._formatUrl( options.url );
        return $( '<li/>' ).append(
            $( '<a/>' ).attr( 'href', options.url )
                       .attr( 'target', options.target )
                       .html( options.title )
                       .on( 'click', function( e ) {
                            e.preventDefault();
                            self.model.set( 'show_menu', false );
                            if (options.onclick){
                                options.onclick();
                            } else {
                                Galaxy.frame.add( options );
                            }
                       })
        );
    },

    /** Handle click event */
    _toggleClick: function( e ) {
        var self = this;
        var model = this.model;
        e.preventDefault();
        $( '.tooltip' ).hide();
        model.trigger( 'dispatch', function( m ) {
            model.id !== m.id && m.get( 'menu' ) && m.set( 'show_menu', false );
        });
        if ( !model.get( 'disabled' ) ) {
            if ( !model.get( 'menu' ) ) {
                model.get( 'onclick' ) ? model.get( 'onclick' )() : Galaxy.frame.add( model.attributes );
            } else {
                model.set( 'show_menu', true );
            }
        }
    },

    /** Configures login notification/popover */
    _configurePopover: function() {
        var self = this;
        function buildLink( label, url ) {
            return $( '<div/>' ).append( $( '<a/>' ).attr( 'href', Galaxy.root + url ).html( label ) ).html()
        }
        this.$toggle.popover && this.$toggle.popover( 'destroy' );
        this.model.get( 'disabled' ) && this.$toggle.popover({
            html        : true,
            placement   : 'bottom',
            content     : 'Please ' + buildLink( 'login', 'user/login?use_panels=True' ) + ' or ' +
                                      buildLink( 'register', 'user/create?use_panels=True' ) + ' to use this feature.'
        }).on( 'shown.bs.popover', function() {
            setTimeout( function() { self.$toggle.popover( 'hide' ) }, 5000 );
        });
    },

    /** Url formatting */
    _formatUrl: function( url ) {
        return typeof url == 'string' && url.indexOf( '//' ) === -1 && url.charAt( 0 ) != '/' ? Galaxy.root + url : url;
    },

    /** body tempate */
    _template: function () {
        return  '<ul class="nav navbar-nav">' +
                    '<li class="dropdown">' +
                        '<a class="dropdown-toggle"/>' +
                        '<ul class="dropdown-menu"/>' +
                        '<div class="dropdown-note"/>' +
                    '</li>' +
                '</ul>';
    }
});

return {
    Collection  : Collection,
    Tab         : Tab
};

});
