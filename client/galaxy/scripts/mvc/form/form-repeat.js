/** This class creates a ui component which enables the dynamic creation of portlets */
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc'],
        function(Utils, Table, Portlet, Ui) {
var View = Backbone.View.extend({
    initialize : function(options) {
        var self = this;
        this.options = Utils.merge(options, {
            title       : 'Section',
            empty_text  : 'Not available.',
            max         : null,
            min         : null
        });
        this.setElement('<div/>');

        // create button
        this.button_new = new Ui.ButtonIcon({
            icon    : 'fa-plus',
            title   : 'Insert ' + this.options.title_new,
            tooltip : 'Add new ' + this.options.title_new + ' block',
            floating: 'clear',
            onclick : function() {
                if (options.onnew) {
                    options.onnew();
                }
            }
        });

        // create table
        this.table = new Table.View({
            cls     : 'ui-table-plain',
            content : ''
        });
        this.$el.append(this.table.$el);
        this.$el.append($('<div/>').append(this.button_new.$el));

        // reset list
        this.list = {};
        this.n = 0;
    },

    /** Number of repeat blocks */
    size: function() {
        return this.n;
    },

    /** Add new repeat block */
    add: function(options) {
        if (!options.id || this.list[options.id]) {
            Galaxy.emit.debug('form-repeat::add()', 'Duplicate repeat block id.');
            return;
        }
        this.n++;
        var button_delete = new Ui.ButtonIcon({
            icon    : 'fa-trash-o',
            tooltip : 'Delete this repeat block',
            cls     : 'ui-button-icon-plain',
            onclick : function() {
                if (options.ondel) {
                    options.ondel();
                }
            }
        });
        var portlet = new Portlet.View({
            id              : options.id,
            title           : 'placeholder',
            cls             : options.cls || 'ui-portlet-repeat',
            operations      : {
                button_delete : button_delete
            }
        });
        portlet.append(options.$el);
        portlet.$el.addClass('section-row');
        this.list[options.id] = portlet;
        this.table.add(portlet.$el);
        this.table.append('row_' + options.id, true);
        if (this.options.max > 0 && this.n >= this.options.max) {
            this.button_new.disable();
        }
        this._refresh();
    },

    /** Delete repeat block */
    del: function(id) {
        if (!this.list[id]) {
            Galaxy.emit.debug('form-repeat::del()', 'Invalid repeat block id.');
            return;
        }
        this.n--;
        var table_row = this.table.get('row_' + id);
        table_row.remove();
        delete this.list[id];
        this.button_new.enable();
        this._refresh();
    },

    /** Remove all */
    delAll: function() {
        for( var id in this.list ) {
            this.del( id );
        }
    },

    /** Hides add/del options */
    hideOptions: function() {
        this.button_new.$el.hide();
        _.each( this.list, function( portlet ) {
            portlet.hideOperation('button_delete');
        });
        if( _.isEmpty( this.list ) ) {
            this.$el.append( $('<div/>').addClass( 'ui-form-info' ).html( this.options.empty_text ) );
        }
    },

    /** Refresh view */
    _refresh: function() {
        var index = 0;
        for (var id in this.list) {
            var portlet = this.list[id];
            portlet.title(++index + ': ' + this.options.title);
            if (this.n > this.options.min) {
                portlet.showOperation('button_delete');
            } else {
                portlet.hideOperation('button_delete');
            }
        }
    }
});

return {
    View : View
}

});
