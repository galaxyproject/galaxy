<template>
<div>
    {{ editorConfig }}
</div>
</template>
<script>
import { urlData } from "utils/url";
import Query from "utils/query-string-parsing";
import Index from "components/Workflow/Editor/Index.vue";
export default {
    data() {
        return {
            editorConfig: {},
        }
    },
    created() {
        this.getState();
    },
    methods: {
        async getState() {
            const workflowId = Query.get("id");
            this.editorConfig = await urlData({ url: `workflow/editor?id=${workflowId}` });
        },
    },
};
</script>
