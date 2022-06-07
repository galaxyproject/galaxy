<template>
    <CurrentUser v-slot="{ user }">
        <StoredWorkflowDetailsProvider v-slot="{ result: item, loading }" :stored-workflow-id="storedWorkflowId">
            <Invocations
                v-if="!loading && user.id"
                :user-id="user.id"
                :stored-workflow-id="item.id"
                :stored-workflow-name="item.name" />
        </StoredWorkflowDetailsProvider>
    </CurrentUser>
</template>
<script>
import Invocations from "components/Workflow/Invocations";
import CurrentUser from "components/providers/CurrentUser";
import { StoredWorkflowDetailsProvider } from "components/providers/StoredWorkflowsProvider";

export default {
    components: {
        CurrentUser,
        Invocations,
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
