<template>
    <!-- Bit of an odd component, but the API returns all invocations for admins if no user id is included in request-->
    <CurrentUser v-slot="{ user }"> <InvocationsList v-if="user.id" :user-id="user.id" /> </CurrentUser>
</template>
<script>
import InvocationsList from "components/Workflow/InvocationsList";
import CurrentUser from "components/providers/CurrentUser";

export default {
    components: {
        CurrentUser,
        InvocationsList,
    },
};
</script>
