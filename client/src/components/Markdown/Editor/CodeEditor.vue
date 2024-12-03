<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
//@ts-ignore
import Prism from "prismjs";
import "prismjs/components/prism-json"; // Load the language
import "prismjs/plugins/line-numbers/prism-line-numbers.css"; // Line numbers plugin styles
import "prismjs/plugins/line-numbers/prism-line-numbers"; // Line numbers plugin

// Props to pass initial content
const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

// References
const editor = ref<HTMLElement | null>(null);
const highlightedContent = ref(props.content);

function render() {
    highlightedContent.value = Prism.highlight(props.content, Prism.languages.json, "json");
}

// Setup Prism.js
onMounted(() => {
    render();
});

// Re-highlight when content changes
watch(() => props.content, () => {
    render();
});
</script>

<template>
    <div contenteditable="true" ref="editor" class="prism-editor">
        <pre class="language-json line-numbers" style="background: transparent"><code v-html="highlightedContent"></code></pre>
    </div>
</template>

<style>
.prism-editor {
    font-family: monospace;
    white-space: pre-wrap;
    overflow-x: auto;
}


/* Line Numbers Styling */
pre.line-numbers {
    position: relative;
    padding-left: 3.8em !important; /* Adjust depending on line number width */
    counter-reset: linenumber;
}

pre.line-numbers > code {
    position: relative;
    display: block;
    padding-left: 0;
}

.line-numbers-rows {
    position: absolute;
    pointer-events: none;
    top: 0;
    left: 0;
    width: 3em;
    border-right: 1px solid #ddd;
    color: #999;
    font-size: 0.875em;
    line-height: 1.5;
    text-align: right;
}

/* Indent Guides Styling */
.prism-editor code {
    background: transparent;
    position: relative;
}

.prism-editor code span.indent-guide {
    display: inline-block;
    width: 1em;
    margin-left: -1em;
    color: #ccc;
    pointer-events: none;
    font-size: 0.9em;
}
</style>

