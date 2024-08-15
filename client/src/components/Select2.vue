<template>
    <select>
        <slot></slot>
    </select>
</template>

<script>
// Based on https://vuejs.org/v2/examples/select2.html but adapted to handle list values
// with "multiple: true" set.
import $ from "jquery";

export default {
    props: ["options", "value", "placeholder", "containerClass", "enabled"],
    watch: {
        value: function (value) {
            // update value
            $(this.$el).val(value);
        },
        options: function (options) {
            // update options
            $(this.$el).empty().select2({ data: options });
        },
        enabled: function (value) {
            $(this.$el).select2("enable", value);
        },
    },
    mounted: function () {
        const vm = this;
        // TODO: refactor property list to objects that allow defaults and types
        let enabled = this.enabled;
        if (enabled === undefined) {
            enabled = true;
        }
        const select2Options = {
            data: this.options,
            placeholder: this.placeholder,
            allowClear: !!this.placeholder,
            enable: enabled,
            dropdownAutoWidth: true,
        };
        if (this.containerClass) {
            select2Options.containerCssClass = this.containerClass;
        }
        $(this.$el)
            // init select2
            .select2(select2Options)
            .val(this.value)
            .trigger("change")
            // emit event on change.
            .on("change", function (event) {
                vm.$emit("input", event.val);
            });
    },
    destroyed: function () {
        $(this.$el).off().select2("destroy");
    },
};
</script>
