<template>
    <div contenteditable="true" ref="editor" class="prism-editor">
      <pre class="language-json line-numbers"><code v-html="highlightedContent"></code></pre>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, onMounted, watch } from "vue";
  //@ts-ignore
  import Prism from "prismjs";
  import "prismjs/themes/prism-coy.css"; // Choose your theme
  import "prismjs/components/prism-json"; // Load the language
  import "prismjs/plugins/line-numbers/prism-line-numbers.css"; // Line numbers plugin styles
  import "prismjs/plugins/line-numbers/prism-line-numbers"; // Line numbers plugin
  
  // Props for initial content
  const props = defineProps({
    content: {
      type: String,
      required: true,
    },
  });
  
  // Refs
  const editor = ref<HTMLElement | null>(null);
  const highlightedContent = ref(props.content);
  
  // Helper function to add indent guides
  function addIndentGuides(content: string): string {
    return content.replace(/^(\s+)/gm, (match) => {
      return match
        .split("")
        .map(() => '<span class="indent-guide">|</span>')
        .join("");
    });
  }
  
  // Watch for content changes and re-highlight
  watch(() => props.content, () => {
    highlightedContent.value = addIndentGuides(
      Prism.highlight(props.content, Prism.languages.json, "json")
    );
  });
  
  // Initialize Prism.js highlighting on mount
  onMounted(() => {
    highlightedContent.value = addIndentGuides(
      Prism.highlight(props.content, Prism.languages.json, "json")
    );
  });
  </script>
  
  <style scoped>
  /* Editor Styling */
  .prism-editor {
    border: 1px solid #ccc;
    background: #f9f9f9;
    font-family: monospace;
    padding: 1rem;
    white-space: pre-wrap;
    overflow-x: auto;
    border-radius: 5px;
    position: relative;
  }
  
  /* Line Numbers Styling */
  pre.line-numbers {
    position: relative;
    padding-left: 3.8em !important; /* Adjust for line number width */
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
  