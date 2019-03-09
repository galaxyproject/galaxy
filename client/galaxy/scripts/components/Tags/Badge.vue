<template>
    <span class="badge badge-tags" :style="tagStyles" 
        @click.prevent="$emit('tag-click', tag)">
        {{ tag }}
    </span>
</template>

<script>

import { generateTagStyle } from "utils/utils";

export default {
    props: {
        tag: { type: String, required: true }
    },
    computed: {
        tagStyles() {
            return generateTagStyle(this.tag);
        }
    }
}

</script>

<style lang="scss">

.badge {
    background-color: #3189a3;
    padding: 0.2em 0.6em 0.3em;
    border-radius: 0.15rem;
    text-decoration: none;
}

</style>
