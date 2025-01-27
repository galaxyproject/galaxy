<script setup lang="ts">
import MarkdownIt from "markdown-it";
//@ts-ignore
import markdownItRegexp from "markdown-it-regexp";
import { computed } from "vue";

const mdNewline = markdownItRegexp(/<br>/, () => {
    return "<div style='clear:both;'/><br>";
});

const md = MarkdownIt();
md.use(mdNewline);

const props = defineProps<{
    content: string;
}>();

const renderedContent = computed(() => md.render(props.content));
</script>

<template>
    <p class="text-justify" v-html="renderedContent" />
</template>
