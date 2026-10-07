<script setup lang="ts">
import { computed } from "vue";

import { markup } from "./configurationMarkdown";

interface Props {
    markdown: string;
    admin: boolean; // was the configuration specified by an admin
}
const props = defineProps<Props>();
const markdownHtml = computed(() => markup(props.markdown ?? "", props.admin));
</script>
<template>
    <div v-sanitize-html:links="markdownHtml" />
</template>
