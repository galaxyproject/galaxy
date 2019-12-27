<template>
    <div ref="content"></div>
</template>

<script>
import $ from "jquery";

export default {
    props: {
        viewClass: {
            type: Function,
            required: true
        },
        app: {
            type: Object,
            required: true
        }
    },
    mounted() {
        // can't just pass in app directly because Vue doesn't like Backbone proping it
        // for properties to auto-populate on child View.
        $(this.$refs.content).append(new this.viewClass({ app: this.app }).$el);
    }
};
</script>
