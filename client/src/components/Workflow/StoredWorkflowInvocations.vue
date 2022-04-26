<template>
    <CurrentUser v-slot="{ user }">
        <StoredWorkflowDetailsProvider :storedWorkflowId="storedWorkflowId" v-slot="{ result: item, loading }">
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
    props: {
        storedWorkflowId: {
            type: String,
            required: true,
        },
    },
    components: {
        CurrentUser,
        Invocations,
        StoredWorkflowDetailsProvider,
    },
};
</script>
