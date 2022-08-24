<template>
    <div class="m-3">
        <ChangePassword v-if="hasToken" />
        <LoginIndex v-else />
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import LoginIndex from "components/login/LoginIndex";
import ChangePassword from "components/login/ChangePassword";

export default {
    components: {
        ChangePassword,
        LoginIndex,
    },
    computed: {
        hasToken() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.params.token || Galaxy.params.expired_user;
        },
    },
};
</script>
