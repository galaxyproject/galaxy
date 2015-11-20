// dependencies
define([], function() {

/** GalaxyMenu uses the GalaxyMasthead class in order to add menu items and icons to the Masthead **/
var GalaxyMenu = Backbone.Model.extend({
    initialize: function( options ) {
        this.options = options.config;
        this.masthead  = options.masthead;
        this.create();
    },

    // default menu
    create: function() {
        //
        // Analyze data tab.
        //
        var tab_analysis = new GalaxyMastheadTab({
            id              : 'analysis',
            title           : 'Analyze Data',
            content         : '',
            title_attribute : 'Analysis home view'
        });
        this.masthead.append( tab_analysis );

        //
        // Workflow tab.
        //

        var workflow_options = {
            id              : 'workflow',
            title           : 'Workflow',
            content         : 'workflow',
            title_attribute : 'Chain tools into workflows'
        }
        if ( !Galaxy.user.id ) {
            workflow_options.disabled = true; // disable workflows for anonymous users
        }

        var tab_workflow = new GalaxyMastheadTab( workflow_options );
        this.masthead.append( tab_workflow );

        //
        // 'Shared Items' or Libraries tab.
        //
        var tab_shared = new GalaxyMastheadTab({
            id              : 'shared',
            title           : 'Shared Data',
            content         : 'library/index',
            title_attribute : 'Access published resources'
        });

        tab_shared.add({
            title   : 'Data Libraries deprecated',
            content : 'library/index'
        });

        tab_shared.add({
            title   : 'Data Libraries',
            content : 'library/list',
            divider : true
        });

        tab_shared.add({
            title   : 'Published Histories',
            content : 'history/list_published'
        });

        tab_shared.add({
            title   : 'Published Workflows',
            content : 'workflow/list_published'

        });

        tab_shared.add({
            title   : 'Published Visualizations',
            content : 'visualization/list_published'
        });

        tab_shared.add({
            title   : 'Published Pages',
            content : 'page/list_published'
        });

        this.masthead.append(tab_shared);

        //
        // Lab menu.
        //
        if ( this.options.user_requests ) {
            var tab_lab = new GalaxyMastheadTab({
                id      : 'lab',
                title   : 'Lab'
            });
            tab_lab.add({
                title   : 'Sequencing Requests',
                content : 'requests/index'
            });
            tab_lab.add({
                title   : 'Find Samples',
                content : 'requests/find_samples_index'
            });
            tab_lab.add({
                title   : 'Help',
                content : this.options.lims_doc_url
            });
            this.masthead.append( tab_lab );
        }

        //
        // Visualization tab.
        //

        var visualization_options = {
            id              : 'visualization',
            title           : 'Visualization',
            content         : 'visualization/list',
            title_attribute : 'Visualize datasets'
        }

        // disable visualizations for anonymous users
        if ( !Galaxy.user.id ) {
            visualization_options.disabled = true;
        }
        var tab_visualization = new GalaxyMastheadTab( visualization_options );

        // add submenu only when user is logged in
        if ( Galaxy.user.id ) {
            tab_visualization.add({
                title   : 'New Track Browser',
                content : 'visualization/trackster',
                target  : '_frame'
            });
            tab_visualization.add({
                title   : 'Saved Visualizations',
                content : 'visualization/list',
                target  : '_frame'
            });
        }
        this.masthead.append( tab_visualization );

        //
        // Admin.
        //
        if ( Galaxy.user.get( 'is_admin' ) ) {
            var tab_admin = new GalaxyMastheadTab({
                id              : 'admin',
                title           : 'Admin',
                content         : 'admin',
                extra_class     : 'admin-only',
                title_attribute : 'Administer this Galaxy'
            });
            this.masthead.append( tab_admin );
        }

        //
        // Help tab.
        //
        var tab_help = new GalaxyMastheadTab({
            id              : 'help',
            title           : 'Help',
            title_attribute : 'Support, contact, and community hubs'
        });
        if ( this.options.biostar_url ){
            tab_help.add({
                title   : 'Galaxy Biostar',
                content : this.options.biostar_url_redirect,
                target  : '_blank'
            });
            tab_help.add({
                title   : 'Ask a question',
                content : 'biostar/biostar_question_redirect',
                target  : '_blank'
            });
        }
        tab_help.add({
            title   : 'Support',
            content : this.options.support_url,
            target  : '_blank'
        });
        tab_help.add({
            title   : 'Search',
            content : this.options.search_url,
            target  : '_blank'
        });
        tab_help.add({
            title   : 'Mailing Lists',
            content : this.options.mailing_lists,
            target  : '_blank'
        });
        tab_help.add({
            title   : 'Videos',
            content : this.options.screencasts_url,
            target  : '_blank'
        });
        tab_help.add({
            title   : 'Wiki',
            content : this.options.wiki_url,
            target  : '_blank'
        });
        tab_help.add({
            title   : 'How to Cite Galaxy',
            content : this.options.citation_url,
            target  : '_blank'
        });
        if (this.options.terms_url){
            tab_help.add({
                title   : 'Terms and Conditions',
                content : this.options.terms_url,
                target  : '_blank'
            });
        }
        this.masthead.append( tab_help );

        //
        // User tab.
        //
        if ( !Galaxy.user.id ){
            var tab_user = new GalaxyMastheadTab({
                id              : 'user',
                title           : 'User',
                extra_class     : 'loggedout-only',
                title_attribute : 'Account registration or login'
            });

            // login
            tab_user.add({
                title   : 'Login',
                content : 'user/login',
                target  : 'galaxy_main'
            });

            // register
            if ( this.options.allow_user_creation ){
                tab_user.add({
                    title   : 'Register',
                    content : 'user/create',
                    target  : 'galaxy_main'
                });
            }

            // add to masthead
            this.masthead.append( tab_user );
        } else {
            var tab_user = new GalaxyMastheadTab({
                id              : 'user',
                title           : 'User',
                extra_class     : 'loggedin-only',
                title_attribute : 'Account preferences and saved data'
            });

            // show user logged in info
            tab_user.add({
                title   : 'Logged in as ' + Galaxy.user.get( 'email' )
            });

            tab_user.add({
                title   : 'Preferences',
                content : 'user?cntrller=user',
                target  : 'galaxy_main'
            });

            tab_user.add({
                title   : 'Custom Builds',
                content : 'user/dbkeys',
                target  : 'galaxy_main'
            });

            tab_user.add({
                title   : 'Logout',
                content : 'user/logout',
                target  : '_top',
                divider : true
            });

            // default tabs
            tab_user.add({
                title   : 'Saved Histories',
                content : 'history/list',
                target  : 'galaxy_main'
            });
            tab_user.add({
                title   : 'Saved Datasets',
                content : 'dataset/list',
                target  : 'galaxy_main'
            });
            tab_user.add({
                title   : 'Saved Pages',
                content : 'page/list',
                target  : '_top'
            });

            tab_user.add({
                title   : 'API Keys',
                content : 'user/api_keys?cntrller=user',
                target  : 'galaxy_main'
            });

            if ( this.options.use_remote_user ){
                tab_user.add({
                    title   : 'Public Name',
                    content : 'user/edit_username?cntrller=user',
                    target  : 'galaxy_main'
                });
            }

            // add to masthead
            this.masthead.append( tab_user );
        }

        // identify active tab
        if ( this.options.active_view ) {
            this.masthead.highlight( this.options.active_view );
        }
    }
});

/** Masthead tab **/
var GalaxyMastheadTab = Backbone.View.extend({
    // main options
    options:{
        id              : '',
        title           : '',
        target          : '_parent',
        content         : '',
        type            : 'url',
        scratchbook     : false,
        onunload        : null,
        visible         : true,
        disabled        : false,
        title_attribute : ''
    },

    // location
    location: 'navbar',

    // optional sub menu
    $menu: null,

    // events
    events:{
        'click .head' : '_head'
    },

    // initialize
    initialize: function ( options ){
        // read in defaults
        if ( options ){
            this.options = _.defaults( options, this.options );
        }

        // update url
        if ( this.options.content !== undefined && this.options.content.indexOf( '//' ) === -1 ){
            this.options.content = Galaxy.root + this.options.content;
        }

        // add template for tab
        this.setElement( $( this._template( this.options ) ) );

        // disable menu items that are not available to anonymous user
        // also show title to explain why they are disabled
        if ( this.options.disabled ){
            $( this.el ).find( '.root' ).addClass( 'disabled' );
            this._attachPopover();
        }

        // visiblity
        if ( !this.options.visible ){
            this.hide();
        }
    },

    // show
    show: function(){
        $(this.el).css({visibility : 'visible'});
    },

    // show
    hide: function(){
        $(this.el).css({visibility : 'hidden'});
    },

    // add menu item
    add: function (options){
        // menu option defaults
        var menuOptions = {
            title       : 'Title',
            content     : '',
            type        : 'url',
            target      : '_parent',
            scratchbook : false,
            divider     : false
        }

        // read in defaults
        if (options)
            menuOptions = _.defaults(options, menuOptions);

        // update url
        if (menuOptions.content && menuOptions.content.indexOf('//') === -1)
            menuOptions.content = Galaxy.root + menuOptions.content;

        // check if submenu element is available
        if (!this.$menu){
            // insert submenu element into root
            $(this.el).find('.root').append(this._templateMenu());

            // show caret
            $(this.el).find('.symbol').addClass('caret');

            // update element link
            this.$menu = $(this.el).find('.popup');
        }

        // create
        var $item = $(this._templateMenuItem(menuOptions));

        // append menu
        this.$menu.append($item);

        // add events
        var self = this;
        $item.on('click', function(e){
            // prevent default
            e.preventDefault();

            // no modifications if new tab is requested
            if (self.options.target === '_blank')
                return true;

            // load into frame
            Galaxy.frame.add(options);
        });

        // append divider
        if (menuOptions.divider)
            this.$menu.append($(this._templateDivider()));
    },

    // show menu on header click
    _head: function(e){
        // prevent default
        e.preventDefault();

        if (this.options.disabled){
            return // prevent link following if menu item is disabled
        }

        // check for menu options
        if (!this.$menu) {
            Galaxy.frame.add(this.options);
        }
    },

    _attachPopover : function(){
        var $popover_element = $(this.el).find('.head');
        $popover_element.popover({
            html: true,
            content: 'Please <a href="' + Galaxy.root + 'user/login?use_panels=True">log in</a> or <a href="' + Galaxy.root + 'user/create?use_panels=True">register</a> to use this feature.',
            placement: 'bottom'
        }).on('shown.bs.popover', function() { // hooking on bootstrap event to automatically hide popovers after delay
            setTimeout(function() {
                $popover_element.popover('hide');
            }, 5000);
        });
     },

    // fill template header
    _templateMenuItem: function (options){
        return '<li><a href="' + options.content + '" target="' + options.target + '">' + options.title + '</a></li>';
    },

    // fill template header
    _templateMenu: function (){
        return '<ul class="popup dropdown-menu"></ul>';
    },

    _templateDivider: function(){
        return '<li class="divider"></li>';
    },

    // fill template
    _template: function (options){
        // start template
        var tmpl =  '<ul id="' + options.id + '" class="nav navbar-nav" border="0" cellspacing="0">' +
                        '<li class="root dropdown" style="">' +
                            '<a class="head dropdown-toggle" data-toggle="dropdown" target="' + options.target + '" href="' + options.content + '" title="' + options.title_attribute + '">' +
                                options.title + '<b class="symbol"></b>' +
                            '</a>' +
                        '</li>' +
                    '</ul>';

        // return template
        return tmpl;
    }
});

// return
return {
    GalaxyMenu: GalaxyMenu,
    GalaxyMastheadTab: GalaxyMastheadTab
};

});
