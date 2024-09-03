<script setup>
import { useFormattedToolHelp } from "composables/formattedToolHelp";

const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

const { formattedContent } = useFormattedToolHelp(props.content);
</script>

<template>
    <div class="form-help form-text" v-html="formattedContent" />
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.form-help {
    &:deep(h3) {
        font-size: $h4-font-size;
        font-weight: bold;
    }

    &:deep(h4) {
        font-size: $h5-font-size;
        font-weight: bold;
    }

    &:deep(h5) {
        font-size: $h6-font-size;
        font-weight: bold;
    }

    &:deep(h6) {
        font-size: $h6-font-size;
        text-decoration: underline;
    }
}
</style>
