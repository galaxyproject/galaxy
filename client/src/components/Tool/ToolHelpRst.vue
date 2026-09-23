<script setup>
import { useFormattedToolHelp } from "@/composables/formattedToolHelp";

const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

const { formattedContent } = useFormattedToolHelp(props.content);
</script>

<template>
    <div v-sanitize-html:links="formattedContent" class="form-help form-text" />
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.form-help {
    &:deep(h3) {
        font-size: $h4-font-size;
        font-weight: bold;
    }

    &:deep(h4) {
        font-size: $h5-font-size;
        font-weight: bold;
    }

    &:deep(h5),
    &:deep(h6) {
        font-size: $h6-font-size;
        font-weight: bold;
    }
}
</style>
