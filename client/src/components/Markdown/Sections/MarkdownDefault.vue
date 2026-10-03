<script setup lang="ts">
import MarkdownIt from "markdown-it";
//@ts-ignore
import markdownItRegexp from "markdown-it-regexp";
import { computed, inject, ref, watch } from "vue";

import { useGxUris } from "@/components/Markdown/gxuris";
import { resolveInlineDirectives } from "@/components/Markdown/Utilities/resolveInlineDirectives";
import { useInvocationStore } from "@/stores/invocationStore";

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

// Inject invocationId from parent (e.g., InvocationReport.vue)
const invocationId = inject<string | undefined>("invocationId", undefined);

const { getInvocationById, fetchInvocationById } = useInvocationStore();

// Fetch the invocation data when invocationId is available
watch(
    () => invocationId,
    async (id) => {
        if (id) {
            await fetchInvocationById({ id });
        }
    },
    { immediate: true },
);

// Get invocation data for resolution
const invocation = computed(() => (invocationId ? getInvocationById(invocationId) : undefined));

// Resolve inline directives using invocation context
const processedContent = computed(() => {
    return resolveInlineDirectives(props.content, invocation.value);
});

const renderedContent = computed(() => md.render(processedContent.value));

const renderedMarkdownDiv = ref<HTMLDivElement>();
const { internalHelpReferences, MarkdownHelpPopovers } = useGxUris(renderedMarkdownDiv);
</script>

<template>
    <span>
        <div
            ref="renderedMarkdownDiv"
            v-sanitize-html:markdown="renderedContent"
            class="text-justify markdown-rendered-content" />
        <MarkdownHelpPopovers :elements="internalHelpReferences" />
    </span>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

// markdown-it emits plain <table> elements with no class, so they get no
// Bootstrap .table styling and no border at all by default. $table-border-color
// is intentionally transparent in this theme (see blue.scss), so it is not
// reused here; $border-color is the same value WorkflowEmbed.vue uses for a
// visible border.
.markdown-rendered-content :deep(table) {
    border-collapse: collapse;
}

.markdown-rendered-content :deep(table th),
.markdown-rendered-content :deep(table td) {
    border: 1px solid $border-color;
    padding: 0.375rem 0.75rem;
}
</style>
