// dependencies
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc'],
        function(Utils, Table, Portlet, Ui) {

/** This class creates a ui component which enables the dynamic creation of portlets
*/
var View = Backbone.View.extend({
    // default options
    optionsDefault : {
        title   : 'Section',
        max     : null,
        min     : null
    },

    /** Initialize
    */
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement('<div/>');

        // link this
        var self = this;

        // create button
        this.button_new = new Ui.ButtonIcon({
            icon    : 'fa-plus',
            title   : 'Insert ' + options.title_new,
            tooltip : 'Add new ' + options.title_new + ' block',
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

        // append button
        this.$el.append(this.table.$el);

        // add button
        this.$el.append($('<div/>').append(this.button_new.$el));

        // clear list
        this.list = {};

        // number of available repeats
        this.n = 0;
    },

    /** Number of repeat blocks
    */
    size: function() {
        return this.n;
    },

    /** Add new repeat block
    */
    add: function(options) {
        // repeat block already exists
        if (!options.id || this.list[options.id]) {
            Galaxy.emit.debug('form-repeat::add()', 'Duplicate repeat block id.');
            return;
        }

        // increase repeat block counter
        this.n++;

        // delete button
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

        // create portlet
        var portlet = new Portlet.View({
            id              : options.id,
            title           : 'placeholder',
            cls             : 'ui-portlet-repeat',
            operations      : {
                button_delete : button_delete
            }
        });

        // append content
        portlet.append(options.$el);

        // tag as section row
        portlet.$el.addClass('section-row');

        // append to dom
        this.list[options.id] = portlet;

        // append to dom
        this.table.add(portlet.$el);
        this.table.append('row_' + options.id, true);

        // validate maximum
        if (this.options.max > 0 && this.n >= this.options.max) {
            this.button_new.disable();
        }

        // refresh view
        this._refresh();
    },

    /** Delete repeat block
    */
    del: function(id) {
        // could not find element
        if (!this.list[id]) {
            Galaxy.emit.debug('form-repeat::del()', 'Invalid repeat block id.');
            return;
        }

        // decrease repeat block counter
        this.n--;

        // delete table row
        var table_row = this.table.get('row_' + id);
        table_row.remove();

        // remove from list
        delete this.list[id];

        // enable new button
        this.button_new.enable();

        // refresh delete button visibility
        this._refresh();
    },

    /** Refresh view
    */
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
