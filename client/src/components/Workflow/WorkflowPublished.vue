<template>
    <Published :details="contentDetails">
        <template v-slot>
            <WorkflowDisplay :args="{ workflow_id: id }" :workflow="contentDetails" :expanded="true" />
        </template>
    </Published>
</template>

<script>
import { urlData } from "utils/url";
import Published from "components/Common/Published";
import WorkflowDisplay from "components/Markdown/Elements/Workflow/WorkflowDisplay";

export default {
    components: {
        Published,
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
            contentDetails: {},
        };
    },
    created() {
        const url = `/api/workflows/${this.id}`;
        urlData({ url }).then((data) => {
            this.contentDetails = { ...data };
        });
    },
};
</script>
