<template>
    <iframe
        :id="id"
        :name="id"
        :src="srcWithRoot"
        class="center-frame"
        frameborder="0"
        title="galaxy frame"
        width="100%"
        height="100%"
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
                if (location && location.host && location.pathname != "/") {
                    this.$emit("load");
                }
            } catch (err) {
                console.warn("CenterFrame - onLoad location access forbidden.", ev, location);
            }
        },
    },
};
</script>
