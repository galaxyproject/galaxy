<template>
    <div ref="editorContainer" class="editor-container"></div>
</template>

<script>
import loader from "@monaco-editor/loader";
import { markRaw } from "vue";

export default {
    props: {
        language: {
            type: String,
            required: true,
        },
        code: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            editor: null,
        };
    },
    watch: {
        code(newValue) {
            if (this.editor) {
                this.editor.setValue(newValue);
            }
        },
        language(newValue) {
            if (this.editor) {
                this.editor.setModelLanguage(this.editor.getModel(), newValue);
            }
        },
    },
    mounted() {
        this.initMonaco();
    },
    beforeUnmount() {
        if (this.editor) {
            this.editor.dispose();
        }
    },
    methods: {
        initMonaco() {
            loader.init().then((monaco) => {
                // Calls through a reactive proxy of Monaco hang the tab, so keep it raw.
                this.editor = markRaw(
                    monaco.editor.create(this.$refs.editorContainer, {
                        value: this.code,
                        language: this.language,
                        readOnly: true,
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        theme: "vs",
                    }),
                );
            });
        },
    },
};
</script>

<style scoped>
.editor-container {
    width: 100%;
    flex: 1 1 0;
    min-height: 0;
}
</style>
