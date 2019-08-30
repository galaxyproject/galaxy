<template>
    <statelesstags :value="workflow.tags" @input="onInput" />
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import StatelessTags from "components/Tags/StatelessTags.vue";
export default {
    components: {
        statelesstags: StatelessTags
    },
    props: ["workflow"],
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
    },
    methods: {
        onInput: function(tags) {
            const id = this.workflow.id;
            const show_in_tool_panel = this.workflow.show_in_tool_panel;
            this.workflow.tags = tags;
            this.services
                .updateWorkflow(id, {
                    show_in_tool_panel: show_in_tool_panel,
                    tags: tags
                })
                .catch(error => {
                    this.$emit("onError", error);
                });
        }
    }
};
</script>
