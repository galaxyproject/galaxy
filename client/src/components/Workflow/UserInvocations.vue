<template>
    <!-- Bit of an odd component, but the API returns all invocations for admins if no user id is included in request-->
    <InvocationsList v-if="currentUser?.id" :user-id="currentUser.id" />
</template>
<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import InvocationsList from "components/Workflow/InvocationsList";

export default {
    components: {
        InvocationsList,
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
    },
};
</script>
