<template>
    <div ref="editorContainer" class="editor-container"></div>
</template>

<script>
import loader from "@monaco-editor/loader";

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
    beforeDestroy() {
        if (this.editor) {
            this.editor.dispose();
        }
    },
    methods: {
        initMonaco() {
            loader.init().then((monaco) => {
                this.editor = monaco.editor.create(this.$refs.editorContainer, {
                    value: this.code,
                    language: this.language,
                    readOnly: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    theme: "vs",
                });
            });
        },
    },
};
</script>

<style scoped>
.editor-container {
    width: 100%;
    height: 600px;
}
</style>
