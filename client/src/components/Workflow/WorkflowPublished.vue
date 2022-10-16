<template>
    <Published :item="workflow" @set-rating="onSetRating">
        <template v-slot>
            <WorkflowDisplay :args="{ workflow_id: id }" :workflow="workflow" :expanded="true" />
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
            workflow: {},
        };
    },
    created() {
        const url = `/api/workflows/${this.id}`;
        const query = this.$route.query;
        urlData({ url }).then((data) => {
            this.workflow = { ...data, ...query };
        });
    },
    methods: {
        onSetRating(newRating) {
            const url = `/workflow/rate_async?id=${this.id}&rating=${newRating}`;
            urlData({ url });
        },
    },
};
</script>
