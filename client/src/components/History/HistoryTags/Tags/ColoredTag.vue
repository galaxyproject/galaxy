<template>
    <b-form-tag pill :style="tagStyle(tag)" v-on="$listeners" v-bind="$attrs">{{ tag }}</b-form-tag>
</template>

<script>
import { BFormTag } from "bootstrap-vue";
import { keyedColorScheme } from "utils/color";

export default {
    components: { BFormTag },
    props: {
        tag: { type: String, required: true },
    },
    methods: {
        tagStyle(tag) {
            const { primary, darker, contrasting } = keyedColorScheme(tag);
            return {
                "background-color": primary,
                color: contrasting,
                "border-color": darker,
            };
        },
    },
};
</script>
