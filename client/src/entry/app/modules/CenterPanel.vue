<template>
    <iframe
        id="galaxy_main"
        name="galaxy_main"
        frameborder="0"
        class="center-frame"
        title="galaxy main frame"
        :src="srcWithRoot"
        @load="onLoad" />
</template>
<script>
import { getAppRoot } from "onload";
export default {
    props: {
        src: {
            type: String,
            default: "",
        },
    },
    computed: {
        srcWithRoot() {
            return `${getAppRoot()}${this.src}`;
        },
    },
    methods: {
        onLoad: function (ev) {
            const iframe = ev.currentTarget;
            const location = iframe.contentWindow && iframe.contentWindow.location;
            try {
                if (location && location.host && location.pathname != "/") {
                    this.$emit("load");
                }
            } catch (err) {
                console.warn("CenterPanel - onLoad location access forbidden.", ev, location);
            }
        },
    },
};
</script>
