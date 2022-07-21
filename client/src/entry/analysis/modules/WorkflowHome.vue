<template>
    <div>
        <b v-localized>Workflows</b>
        <workflow-list :simplified="true" />
        <b v-localized>Invocations</b>
        <invocations :showTitle="false" :simplified="true" />
    </div>
</template>

<script>
import WorkflowList from "components/Workflow/WorkflowList";
import Invocations from "components/Workflow/Invocations";

export default {
    components: {
        WorkflowList,
        Invocations,
    },
    data() {
        return {};
    },
};
</script>
