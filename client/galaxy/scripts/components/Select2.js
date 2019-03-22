// Based on https://vuejs.org/v2/examples/select2.html but adapted to handle list values
// with "multiple: true" set.
import $ from "jquery";

export default {
    props: ["options", "value", "placeholder"],
    template: `<select><slot></slot></select>`,
    mounted: function() {
        var vm = this;
        $(this.$el)
            // init select2
            .select2({ data: this.options, placeholder: this.placeholder, allowClear: this.placeholder })
            .val(this.value)
            .trigger("change")
            // emit event on change.
            .on("change", function(event) {
                vm.$emit("input", event.val);
            });
    },
    watch: {
        value: function(value) {
            // update value
            $(this.$el).val(value);
        },
        options: function(options) {
            // update options
            $(this.$el)
                .empty()
                .select2({ data: options });
        }
    },
    destroyed: function() {
        $(this.$el)
            .off()
            .select2("destroy");
    }
};
