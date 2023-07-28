<template>
    <PublishedItem :item="workflow">
        <template v-slot>
            <WorkflowDisplay :workflow-id="id" :expanded="true" />
        </template>
    </PublishedItem>
</template>

<script>
import { urlData } from "@/utils/url";

import PublishedItem from "@/components/Common/PublishedItem.vue";
import WorkflowDisplay from "@/components/Markdown/Elements/Workflow/WorkflowDisplay.vue";

export default {
    components: {
        PublishedItem,
        WorkflowDisplay,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            workflow: {},
        };
    },
    created() {
        const url = `/api/workflows/${this.id}`;
        urlData({ url }).then((data) => {
            this.workflow = data;
        });
    },
};
</script>
