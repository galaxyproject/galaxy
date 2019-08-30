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
            this.workflow.tags = tags;
            this.services
                .updateWorkflow(
                    workflow.id,
                    (data = {
                        tags: tags
                    })
                )
                .catch(error => {
                    this.onError(error);
                });
        }
    }
};
</script>
