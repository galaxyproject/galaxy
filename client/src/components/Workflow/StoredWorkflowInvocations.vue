<template>
    <StoredWorkflowDetailsProvider v-slot="{ result: item, loading }" :stored-workflow-id="storedWorkflowId">
        <InvocationsList
            v-if="!loading && currentUser.id"
            :user-id="currentUser.id"
            :stored-workflow-id="item.id"
            :stored-workflow-name="item.name" />
    </StoredWorkflowDetailsProvider>
</template>
<script>
import { StoredWorkflowDetailsProvider } from "components/providers/StoredWorkflowsProvider";
import InvocationsList from "components/Workflow/InvocationsList";
import { mapState } from "pinia";

import { useUserStore } from "@/stores/userStore";

export default {
    components: {
        InvocationsList,
        StoredWorkflowDetailsProvider,
    },
    props: {
        storedWorkflowId: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
    },
};
</script>
