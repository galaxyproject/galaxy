<template>
    <iframe
        :id="id"
        :name="id"
        :src="srcWithRoot"
        class="center-frame"
        frameborder="0"
        title="galaxy frame"
        :width="width"
        :height="height"
        sandbox="allow-scripts allow-same-origin allow-forms"
        @load="onLoad" />
</template>
<script>
import { withPrefix } from "utils/redirect";

export default {
    props: {
        id: {
            type: String,
            default: "frame",
        },
        src: {
            type: String,
            default: "",
        },
        width: {
            type: String,
            default: "100%",
        },
        height: {
            type: String,
            default: "100%",
        },
    },
    computed: {
        srcWithRoot() {
            return withPrefix(this.src);
        },
    },
    methods: {
        onLoad(ev) {
            const iframe = ev.currentTarget;
            const location = iframe.contentWindow && iframe.contentWindow.location;
            try {
                if (location && location.pathname !== "/") {
                    this.$emit("load");
                }
            } catch (err) {
                console.warn("CenterFrame - onLoad location access forbidden.", ev, location);
            }
        },
    },
};
</script>
