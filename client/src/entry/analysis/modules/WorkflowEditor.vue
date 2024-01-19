<template>
    <Editor
        v-if="editorConfig"
        :key="editorConfig.id"
        :workflow-id="editorConfig.id"
        :data-managers="editorConfig.dataManagers"
        :initial-version="editorConfig.initialVersion"
        :module-sections="editorConfig.moduleSections"
        :workflow-tags="editorConfig.tags"
        :workflows="editorConfig.workflows"
        @update:confirmation="$emit('update:confirmation', $event)" />
</template>
<script>
import Editor from "components/Workflow/Editor/Index";
import { urlData } from "utils/url";

export default {
    components: {
        Editor,
    },
    props: {
        id: {
            type: String,
            default: undefined,
        },
        workflowId: {
            type: String,
            default: undefined,
        },
    },
    data() {
        return {
            editorConfig: null,
        };
    },
    watch: {
        id: {
            handler() {
                this.getEditorConfig();
            },
            immediate: true,
        },
        workflowId: {
            handler() {
                this.getEditorConfig();
            },
            immediate: true,
        },
    },
    methods: {
        async getEditorConfig() {
            const params = {};
            if (this.workflowId) {
                params.workflow_id = this.workflowId;
            } else if (this.id) {
                params.id = this.id;
            }
            this.editorConfig = await urlData({ url: "/workflow/editor", params });
        },
    },
};
</script>
