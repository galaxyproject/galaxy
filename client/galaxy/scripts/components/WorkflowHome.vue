<template>
    <div>
        <b>Workflows</b>
        <workflow-list :simplified="true" />
        <b>Invocations</b>
        <recent-invocations :showTitle="false" :simplified="true" />
    </div>
</template>

<script>
import WorkflowList from "components/Workflow/WorkflowList";
import RecentInvocations from "components/User/RecentInvocations";

export default {
    components: {
        WorkflowList,
        RecentInvocations,
    },
    data() {
        return {};
    },
};
</script>
