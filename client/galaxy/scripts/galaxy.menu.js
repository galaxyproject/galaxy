// dependencies
define(['galaxy.masthead'], function( Masthead ) {

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
        var tab_analysis = new Masthead.GalaxyMastheadTab({
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

        var tab_workflow = new Masthead.GalaxyMastheadTab( workflow_options );
        this.masthead.append( tab_workflow );

        //
        // 'Shared Items' or Libraries tab.
        //
        var tab_shared = new Masthead.GalaxyMastheadTab({
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
            var tab_lab = new Masthead.GalaxyMastheadTab({
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
        var tab_visualization = new Masthead.GalaxyMastheadTab( visualization_options );

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
            var tab_admin = new Masthead.GalaxyMastheadTab({
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
        var tab_help = new Masthead.GalaxyMastheadTab({
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
            var tab_user = new Masthead.GalaxyMastheadTab({
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
            var tab_user = new Masthead.GalaxyMastheadTab({
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

// return
return {
    GalaxyMenu: GalaxyMenu
};

});
