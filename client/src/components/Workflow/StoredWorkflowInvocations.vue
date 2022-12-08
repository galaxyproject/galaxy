<template>
    <CurrentUser v-slot="{ user }">
        <StoredWorkflowDetailsProvider v-slot="{ result: item, loading }" :stored-workflow-id="storedWorkflowId">
            <InvocationsList
                v-if="!loading && user.id"
                :user-id="user.id"
                :stored-workflow-id="item.id"
                :stored-workflow-name="item.name" />
        </StoredWorkflowDetailsProvider>
    </CurrentUser>
</template>
<script>
import InvocationsList from "components/Workflow/InvocationsList";
import CurrentUser from "components/providers/CurrentUser";
import { StoredWorkflowDetailsProvider } from "components/providers/StoredWorkflowsProvider";

export default {
    components: {
        CurrentUser,
        InvocationsList,
        StoredWorkflowDetailsProvider,
    },
    props: {
        storedWorkflowId: {
            type: String,
            required: true,
        },
    },
};
</script>
