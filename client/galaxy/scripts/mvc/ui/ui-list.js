// dependencies
define(['utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc'], function(Utils, Portlet, Ui) {

// ui list element
var View = Backbone.View.extend({
    // create portlet to keep track of selected list elements
    initialize : function(options) {
        // link this
        var self = this;

        // initialize options
        this.options = options;
        this.name = options.name || 'element';
        this.multiple = options.multiple || false;

        // create message handler
        this.message = new Ui.Message();

        // create portlet
        this.portlet = new Portlet.View({ cls: 'ui-portlet-section' });

        // create select field containing the options which can be inserted into the list
        this.select = new Ui.Select.View({ optional : options.optional });

        // create insert new list element button
        this.button = new Ui.ButtonIcon({
            icon        : 'fa fa-sign-in',
            floating    : 'left',
            tooltip     : 'Insert new ' + this.name,
            onclick     : function() {
                self.add({
                    id      : self.select.value(),
                    name    : self.select.text()
                });
            }
        });

        // build main element
        this.setElement(this._template(options));
        this.$('.ui-list-message').append(this.message.$el);
        this.$('.ui-list-portlet').append(this.portlet.$el);
        this.$('.ui-list-button').append(this.button.$el);
        this.$('.ui-list-select').append(this.select.$el);
    },

    /** Return/Set currently selected list elements */
    value: function(val) {
        // set new value
        if (val !== undefined) {
            this.portlet.empty();
            if ($.isArray(val)) {
                for (var i in val) {
                    var v = val[i];
                    var v_id = null;
                    var v_name = null;
                    if ($.type(v) != 'string') {
                        v_id = v.id;
                        v_name = v.name;
                    } else {
                        v_id = v_name = v;
                    }
                    if (v_id != null) {
                        this.add({
                            id      : v_id,
                            name    : v_name
                        });
                    }
                }
            }
            this._refresh();
        }
        // get current value
        var lst = [];
        this.$('.ui-list-id').each(function() {
            lst.push({
                id      : $(this).prop('id'),
                name    : $(this).find('.ui-list-name').html()
            });
        });
        if (lst.length == 0) {
            return null;
        }
        return lst;
    },

    /** Add row */
    add: function(options) {
        var self = this;
        if (this.$('[id="' + options.id + '"]').length === 0) {
            if (!Utils.isEmpty(options.id)) {
                var $el = $(this._templateRow({
                    id      : options.id,
                    name    : options.name
                }));
                $el.on('click', function() {
                    $el.remove();
                    self._refresh();
                });
                $el.on('mouseover', function() {
                    $el.addClass('portlet-highlight');
                });
                $el.on('mouseout', function() {
                    $el.removeClass('portlet-highlight');
                });
                this.portlet.append($el);
                this._refresh();
            } else {
                this.message.update({ message: 'Please select a valid ' + this.name + '.', status: 'danger' });
            }
        } else {
            this.message.update({ message: 'This ' + this.name + ' is already in the list.' });
        }
    },

    /** Update available options */
    update: function(options) {
        this.select.update(options);
    },

    /** Refresh view */
    _refresh: function() {
        if (this.$('.ui-list-id').length > 0) {
            !this.multiple && this.button.disable();
            this.$('.ui-list-portlet').show();
        } else {
            this.button.enable();
            this.$('.ui-list-portlet').hide();
        }
        this.options.onchange && this.options.onchange();
    },

    /** Main Template */
    _template: function(options) {
        return  '<div class="ui-list">' +
                    '<div class="ui-margin-top">' +
                        '<span class="ui-list-button"/>' +
                        '<span class="ui-list-select"/>' +
                    '</div>' +
                    '<div class="ui-list-message"/>' +
                    '<div class="ui-list-portlet"/>' +
                '</div>';
    },

    /** Row Template */
    _templateRow: function(options) {
        return  '<div id="' + options.id + '" class="ui-list-id">' +
                    '<span class="ui-list-delete fa fa-trash"/>' +
                    '<span class="ui-list-name">' + options.name + '</span>' +
                '</div>';
    }
});

return {
    View: View
}

});
