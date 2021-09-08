<template>
    <span class="badge badge-tags" :style="tagStyles" @click.prevent="$emit('tag-click', tag)">{{ tagLabel }}</span>
</template>

<script>
import { keyedColorScheme } from "utils/color";

export default {
    props: {
        tag: { type: String, required: true },
    },
    computed: {
        tagLabel() {
            return this.tag.startsWith("name:") ? this.tag.replace("name:", "") : this.tag;
        },
        tagStyles() {
            const { primary, contrasting, darker } = keyedColorScheme(this.tag);
            return {
                "background-color": primary,
                color: contrasting,
                "border-color": darker,
            };
        },
    },
};
</script>

<style lang="scss">
.badge {
    padding: 0.2em 0.6em 0.3em;
    border-width: 1px;
    border-style: solid;
    border-radius: 0.15rem;
    text-decoration: none;
}
</style>
