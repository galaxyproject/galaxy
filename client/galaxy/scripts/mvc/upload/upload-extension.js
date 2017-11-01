/** This renders a popover with extension details **/
import Utils from "utils/utils";
import Popover from "mvc/ui/ui-popover";
export default Backbone.View.extend({
    initialize: function(options) {
        this.model = new Backbone.Model(options);
        this.setElement("<div/>");
        this.render();
    },

    render: function() {
        var self = this;
        var options = this.model.attributes;
        var description = _.findWhere(options.list, {
            id: options.extension
        });
        this.extension_popup && this.extension_popup.remove();
        this.extension_popup = new Popover.View({
            placement: options.placement || "bottom",
            container: options.$el
        });
        this.extension_popup.title(options.title);
        this.extension_popup.empty();
        this.extension_popup.append(this._templateDescription(description));
        this.extension_popup.show();
    },

    /** Template for extensions description */
    _templateDescription: function(options) {
        if (options.description) {
            var tmpl = options.description;
            if (options.description_url) {
                tmpl += `&nbsp;(<a href="${options.description_url}" target="_blank">read more</a>)`;
            }
            return tmpl;
        } else {
            return "There is no description available for this file extension.";
        }
    }
});
