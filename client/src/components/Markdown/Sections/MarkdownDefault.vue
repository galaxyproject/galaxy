<script setup lang="ts">
import MarkdownIt from "markdown-it";
//@ts-ignore
import markdownItRegexp from "markdown-it-regexp";
import { computed } from "vue";

//@ts-ignore
import markdownItKatex from "./Plugins/markdown-it-katex";

const mdNewline = markdownItRegexp(/<br>/, () => {
    return "<div style='clear:both;'/><br>";
});

const md = MarkdownIt();
md.use(mdNewline);
md.use(markdownItKatex, { throwOnError: false });

const props = defineProps<{
    content: string;
}>();

const renderedContent = computed(() => md.render(props.content));
</script>

<template>
    <div class="text-justify" v-html="renderedContent" />
</template>
