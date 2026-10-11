<script setup lang="ts">
import loader, { type Monaco } from "@monaco-editor/loader";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

interface Props {
    /** Source code to display */
    code: string;
    /** Monaco language id used for highlighting */
    language: string;
}

const props = defineProps<Props>();

const editorContainer = ref<HTMLDivElement | null>(null);

// Plain variables: Monaco objects must not be wrapped in reactive proxies.
let monacoApi: Monaco | null = null;
let codeEditor: ReturnType<Monaco["editor"]["create"]> | null = null;

function initMonaco() {
    loader.init().then((monaco) => {
        if (!editorContainer.value) {
            return;
        }
        monacoApi = monaco;
        codeEditor = monaco.editor.create(editorContainer.value, {
            value: props.code,
            language: props.language,
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            theme: "vs",
        });
    });
}

watch(
    () => props.code,
    (newValue) => {
        if (codeEditor) {
            codeEditor.setValue(newValue);
        }
    },
);

watch(
    () => props.language,
    (newValue) => {
        const model = codeEditor?.getModel();
        if (monacoApi && model) {
            monacoApi.editor.setModelLanguage(model, newValue);
        }
    },
);

onMounted(() => {
    initMonaco();
});

onBeforeUnmount(() => {
    if (codeEditor) {
        codeEditor.dispose();
    }
});
</script>

<template>
    <div ref="editorContainer" class="editor-container" />
</template>

<style scoped>
.editor-container {
    width: 100%;
    flex: 1 1 0;
    min-height: 0;
}
</style>
