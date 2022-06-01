<template>
    <iframe
        frameborder="0"
        class="center-frame"
        title="galaxy frame"
        :id="id"
        :name="id"
        :src="srcWithRoot"
        @load="onLoad" />
</template>
<script>
import { getAppRoot } from "onload";
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
            if (this.src) {
                return `${getAppRoot()}${this.src}`;
            }
            return undefined;
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
