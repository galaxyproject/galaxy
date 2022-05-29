<template>
    <iframe
        id="galaxy_main"
        name="galaxy_main"
        frameborder="0"
        class="center-frame"
        title="galaxy main frame"
        :src="srcWithRoot"
        @load="$emit('load')" />
</template>
<script>
import { getAppRoot } from "onload";
export default {
    props: {
        src: {
            type: String,
            default: null,
        },
    },
    computed: {
        srcWithRoot() {
            return `${getAppRoot()}${this.src}`;
        },
    },
};
</script>
