define([
    "mvc/ui/popup-menu",
    "mvc/base-mvc",
    "utils/localization"
], function( PopupMenu, BASE_MVC, _l ){
// ============================================================================
var menu = [
    {
        html    : _l( 'History Lists' ),
        header  : true
    },
    {
        html    : _l( 'Saved Histories' ),
        href    : 'history/list'
    },
    {
        html    : _l( 'Histories Shared with Me' ),
        href    : 'history/list_shared'
    },

    {
        html    : _l( 'Current History' ),
        header  : true,
        anon    : true
    },
    {
        html    : _l( 'Create New' ),
        func    : function() {
            if( Galaxy && Galaxy.currHistoryPanel ){
                Galaxy.currHistoryPanel.createNewHistory();
            }
        }
    },
    {
        html    : _l( 'Copy History' ),
        href    : 'history/copy'
    },
    {
        html    : _l( 'Copy Datasets' ),
        href    : 'dataset/copy_datasets'
    },
    {
        html    : _l( 'Share or Publish' ),
        href    : 'history/sharing'
    },
    {
        html    : _l( 'Extract Workflow' ),
        href    : 'workflow/build_from_current_history'
    },
    {
        html    : _l( 'Dataset Security' ),
        href    : 'root/history_set_default_permissions'
    },
    {
        html    : _l( 'Resume Paused Jobs' ),
        href    : 'history/resume_paused_jobs?current=True',
        anon    : true
    },
    {
        html    : _l( 'Collapse Expanded Datasets' ),
        func    : function() {
            if( Galaxy && Galaxy.currHistoryPanel ){
                Galaxy.currHistoryPanel.collapseAll();
            }
        }
    },
    {
        html    : _l( 'Unhide Hidden Datasets' ),
        anon    : true,
        func    : function() {
            if( Galaxy && Galaxy.currHistoryPanel && confirm( _l( 'Really unhide all hidden datasets?' ) ) ){
                var filtered = Galaxy.currHistoryPanel.model.contents.hidden();
                //TODO: batch
                filtered.ajaxQueue( Backbone.Model.prototype.save, { visible : true })
                    .done( function(){
                        Galaxy.currHistoryPanel.renderItems();
                    })
                    .fail( function(){
                        alert( 'There was an error unhiding the datasets' );
                        console.error( arguments );
                    });
            }
        }
    },
    {
        html    : _l( 'Delete Hidden Datasets' ),
        anon    : true,
        func    : function() {
            if( Galaxy && Galaxy.currHistoryPanel && confirm( _l( 'Really delete all hidden datasets?' ) ) ){
                var filtered = Galaxy.currHistoryPanel.model.contents.hidden();
                //TODO: batch
                // both delete *and* unhide them
                filtered.ajaxQueue( Backbone.Model.prototype.save, { deleted : true, visible: true })
                    .done( function(){
                        Galaxy.currHistoryPanel.renderItems();
                    })
                    .fail( function(){
                        alert( 'There was an error deleting the datasets' );
                        console.error( arguments );
                    });
            }
        }
    },
    {
        html    : _l( 'Purge Deleted Datasets' ),
        confirm : _l( 'Really delete all deleted datasets permanently? This cannot be undone.' ),
        href    : 'history/purge_deleted_datasets',
        purge   : true,
        anon    : true
    },
    {
        html    : _l( 'Show Structure' ),
        href    : 'history/display_structured',
        anon    : true
    },
    {
        html    : _l( 'Export Citations' ),
        href    : 'history/citations',
        anon    : true
    },
    {
        html    : _l( 'Export to File' ),
        href    : 'history/export_archive?preview=True',
        anon    : true
    },
    {
        html    : _l( 'Delete' ),
        confirm : _l( 'Really delete the current history?' ),
        href    : 'history/delete_current'
    },
    {
        html    : _l( 'Delete Permanently' ),
        confirm : _l( 'Really delete the current history permanently? This cannot be undone.' ),
        href    : 'history/delete_current?purge=True',
        purge   : true,
        anon    : true
    },

    {
        html    : _l( 'Other Actions' ),
        header  : true
    },
    {
        html    : _l( 'Import from File' ),
        href    : 'history/import_archive'
    }
];

function buildMenu( isAnon, purgeAllowed, urlRoot ){
    return _.clone( menu ).filter( function( menuOption ){
        if( isAnon && !menuOption.anon ){
            return false;
        }
        if( !purgeAllowed && menuOption.purge ){
            return false;
        }

        //TODO:?? hard-coded galaxy_main
        if( menuOption.href ){
            menuOption.href = urlRoot + menuOption.href;
            menuOption.target = 'galaxy_main';
        }
        if( menuOption.confirm ){
            menuOption.func = function(){
                if( confirm( menuOption.confirm ) ){
                    galaxy_main.location = menuOption.href;
                }
            };
        }
        return true;
    });
}

var create = function( $button, options ){
    options = options || {};
    var isAnon = options.anonymous === undefined? true : options.anonymous,
        purgeAllowed = options.purgeAllowed || false,
        root = options.root || ( ( Galaxy && Galaxy.options )? Galaxy.options.root: '/' ),
        menu = buildMenu( isAnon, purgeAllowed, root );
    //console.debug( 'menu:', menu );
    return new PopupMenu( $button, menu );
};


// ============================================================================
    return create;
});
