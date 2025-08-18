<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

import { getGalaxyInstance } from "@/app";
import { useConfig } from "@/composables/config";

import ChangePassword from "@/components/Login/ChangePassword.vue";
import LoginIndex from "@/components/Login/LoginIndex.vue";

const router = useRouter();
const { config, isConfigLoaded } = useConfig();

const hasToken = computed(() => {
    return router.currentRoute.value?.query?.token || router.currentRoute.value?.query?.expired_user;
});
const sessionCsrfToken = computed(() => {
    return getGalaxyInstance().session_csrf_token;
});
const queryAttributeForceString = function (
    queryAttribute: string | (string | null)[] | undefined,
): string | undefined {
    if (Array.isArray(queryAttribute)) {
        return queryAttribute[0] || undefined;
    } else {
        return queryAttribute;
    }
};
</script>

<template>
    <div class="overflow-auto m-3">
        <ChangePassword
            v-if="hasToken"
            id="change-password"
            :expired-user="queryAttributeForceString(router.currentRoute.value?.query?.expired_user)"
            :message-text="queryAttributeForceString(router.currentRoute.value?.query?.message)"
            :message-variant="queryAttributeForceString(router.currentRoute.value?.query?.status)"
            :token="queryAttributeForceString(router.currentRoute.value?.query?.token)" />
        <LoginIndex
            v-else-if="isConfigLoaded"
            id="login-index"
            :allow-user-creation="config.allow_local_account_creation"
            :disable-local-accounts="config.disable_local_accounts"
            :enable-oidc="config.enable_oidc"
            :mailing-join-addr="config.mailing_join_addr"
            :prefer-custos-login="config.prefer_custos_login"
            :redirect="queryAttributeForceString(router.currentRoute.value?.query?.redirect)"
            :registration-warning-message="config.registration_warning_message"
            :session-csrf-token="sessionCsrfToken"
            :show-reset-link="config.enable_account_interface"
            :show-welcome-with-login="config.show_welcome_with_login"
            :terms-url="config.terms_url"
            :welcome-url="config.welcome_url" />
    </div>
</template>
