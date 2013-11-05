/*
    galaxy menu
*/

// dependencies
define(["galaxy.master", "libs/backbone/backbone-relational"], function(mod_master) {

// frame manager
var GalaxyMenu = Backbone.Model.extend(
{
    // options
    options: null,
    
    // link master class
    master: null,
    
    // initialize
    initialize: function(options)
    {
        this.options = options.config;
        this.master  = options.master;
        this.create();
    },
    
    // default menu
    create: function()
    {
        //
        // Analyze data tab.
        //
        var tab_analysis = new mod_master.GalaxyMasterTab({
            title   : "Analyze Data",
            content : "root/index"
        });
        this.master.append(tab_analysis);

        //
        // Workflow tab.
        //
        var tab_workflow = new mod_master.GalaxyMasterTab({
            title   : "Workflow",
            content : "workflow"

        });
        this.master.append(tab_workflow);

        //
        // 'Shared Items' or Libraries tab.
        //
        var tab_shared = new mod_master.GalaxyMasterTab({
            title   : "Shared Data",
            content : "library/index"
        });

        tab_shared.addMenu({
            title   : "Data Libraries",
            content : "library/index",
            divider : true
        });

        tab_shared.addMenu({
            title   : "Published Histories",
            content : "history/list_published"
        });

        tab_shared.addMenu({
            title   : "Published Workflows",
            content : "workflow/list_published"

        });

        tab_shared.addMenu({
            title   : "Published Visualizations",
            content : "visualization/list_published"
        });

        tab_shared.addMenu({
            title   : "Published Pages",
            content : "page/list_published"
        });

        this.master.append(tab_shared);

        //
        // Lab menu.
        //
        if (this.options.user.requests)
        {
            var tab_lab = new mod_master.GalaxyMasterTab({
                title   : "Lab"
            });
            tab_lab.addMenu({
                title   : "Sequencing Requests",
                content : "requests/index"
            });
            tab_lab.addMenu({
                title   : "Find Samples",
                content : "requests/find_samples_index"
            });
            tab_lab.addMenu({
                title   : "Help",
                content : this.options.lims_doc_url
            });
            this.master.append(tab_lab);
        }

        //
        // Visualization tab.
        //
        var tab_visualization = new mod_master.GalaxyMasterTab({

            title       : "Visualization",
            content     : "visualization/list"
        });
        tab_visualization.addMenu({
            title       : "New Track Browser",
            content     : "visualization/trackster",
            target      : "_frame"
        });
        tab_visualization.addMenu({
            title       : "Saved Visualizations",
            content     : "visualization/list",
            target      : "_frame"
        });
        this.master.append(tab_visualization);

        //
        // Cloud menu.
        //
        if (this.options.enable_cloud_launch)
        {
            var tab_cloud = new mod_master.GalaxyMasterTab({
                title   : "Cloud",
                content : "cloudlaunch/index"
            });
            tab_cloud.addMenu({
                title   : "New Cloud Cluster",
                content : "cloudlaunch/index"
            });
            this.master.append(tab_cloud);
        }

        //
        // Admin.
        //
        if (this.options.is_admin_user)
        {
            var tab_admin = new mod_master.GalaxyMasterTab({
                title       : "Admin",
                content     : "admin/index",
                extra_class : "admin-only"
            });
            this.master.append(tab_admin);
        }

        //
        // Help tab.
        //
        var tab_help = new mod_master.GalaxyMasterTab({
            title   : "Help"
        });
        if (this.options.biostar_url)
        {
            tab_help.addMenu({
                title   : "Galaxy Q&A Site",
                content : this.options.biostar_url_redirect,
                target  : "_blank"
            });
            tab_help.addMenu({
                title   : "Ask a question",
                content : "biostar/biostar_question_redirect",
                target  : "_blank"
            });
        }
        tab_help.addMenu({
            title   : "Support",
            content : this.options.support_url,
            target  : "_blank"
        });
        tab_help.addMenu({
            title   : "Search",
            content : this.options.search_url,
            target  : "_blank"
        });
        tab_help.addMenu({
            title   : "Mailing Lists",
            content : this.options.mailing_lists,
            target  : "_blank"
        });
        tab_help.addMenu({
            title   : "Videos",
            content : this.options.screencasts_url,
            target  : "_blank"
        });
        tab_help.addMenu({
            title   : "Wiki",
            content : this.options.wiki_url,
            target  : "_blank"
        });
        tab_help.addMenu({
            title   : "How to Cite Galaxy",
            content : this.options.citation_url,
            target  : "_blank"
        });
        if (!this.options.terms_url)
        {
            tab_help.addMenu({
                title   : "Terms and Conditions",
                content : this.options.terms_url,
                target  : "_blank"
            });
        }
        this.master.append(tab_help);

        //
        // User tab.
        //
        if (!this.options.user.valid)
        {
            var tab_user = new mod_master.GalaxyMasterTab({
                title       : "User",
                extra_class : "loggedout-only"
            });

            // login
            if (this.options.allow_user_creation)
            {
                tab_user.addMenu({
                    title   : "Login",
                    content : "user/login",
                    target  : "galaxy_main"
                });
            }

            // register
            if (this.options.allow_user_creation)
            {
                tab_user.addMenu({
                    title   : "Register",
                    content : "user/create",
                    target  : "galaxy_main"
                });
            }

            // add to master
            this.master.append(tab_user);
        } else {
            var tab_user = new mod_master.GalaxyMasterTab({
                title       : "User",
                extra_class : "loggedin-only"
            });

            // show user logged in info
            tab_user.addMenu({
                title       : "Logged in as " + this.options.user.email
            });

            // remote user
            if (this.options.use_remote_user && this.options.remote_user_logout_href)
            {
                tab_user.addMenu({
                    title   : "Logout",
                    content : this.options.remote_user_logout_href,
                    target  : "_top"
                });
            } else {
                tab_user.addMenu({
                    title   : "Preferences",
                    content : "user?cntrller=user",
                    target  : "galaxy_main"
                });

                tab_user.addMenu({
                    title   : "Custom Builds",
                    content : "user/dbkeys",
                    target  : "galaxy_main"
                });
            
                tab_user.addMenu({
                    title   : "Logout",
                    content : "user/logout",
                    target  : "_top",
                    divider : true
                });
            }
        
            // default tabs
            tab_user.addMenu({
                title   : "Saved Histories",
                content : "history/list",
                target  : "galaxy_main"
            });
            tab_user.addMenu({
                title   : "Saved Datasets",
                content : "dataset/list",
                target  : "galaxy_main"
            });
            tab_user.addMenu({
                title   : "Saved Pages",
                content : "page/list",
                target  : "_top"
            });

            tab_user.addMenu({
                title   : "API Keys",
                content : "user/api_keys?cntrller=user",
                target  : "galaxy_main"
            });

            if (this.options.use_remote_user)
            {
                tab_user.addMenu({
                    title   : "Public Name",
                    content : "user/edit_username?cntrller=user",
                    target  : "galaxy_main"
                });
            }

            // add to master
            this.master.append(tab_user);
        }
    }
});

// return
return {
    GalaxyMenu: GalaxyMenu
};

});
