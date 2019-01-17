import Backbone from "backbone";
var Model = Backbone.Model.extend({
    defaults: {
        extension: "auto",
        genome: "?",
        url_paste: "",
        status: "init",
        info: null,
        file_name: "",
        file_mode: "",
        file_size: 0,
        file_type: null,
        file_path: "",
        file_data: null,
        percentage: 0,
        space_to_tab: false,
        to_posix_lines: true,
        enabled: true
    },
    reset: function(attr) {
        this.clear()
            .set(this.defaults)
            .set(attr);
    }
});
var Collection = Backbone.Collection.extend({ model: Model });
export default { Model: Model, Collection: Collection };
