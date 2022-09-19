<template>
    <!-- Bit of an odd component, but the API returns all invocations for admins if no user id is included in request-->
    <CurrentUser v-slot="{ user }"> <Invocations v-if="user.id" :user-id="user.id" /> </CurrentUser>
</template>
<script>
import Invocations from "components/Workflow/Invocations";
import CurrentUser from "components/providers/CurrentUser";

export default {
    components: {
        CurrentUser,
        Invocations,
    },
};
</script>
