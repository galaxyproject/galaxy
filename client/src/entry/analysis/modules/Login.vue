<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import { useConfig } from "@/composables/config";

import ChangePassword from "@/components/Login/ChangePassword.vue";
import LoginIndex from "@/components/Login/LoginIndex.vue";

const router = useRouter();
const { config, isConfigLoaded } = useConfig();

const hasToken = computed(() => {
    return router.currentRoute.query.token || router.currentRoute.query.expired_user;
});
const sessionCsrfToken = computed(() => {
    return getGalaxyInstance().session_csrf_token;
});
</script>

<template>
    <div class="overflow-auto m-3">
        <ChangePassword
            v-if="hasToken"
            id="change-password"
            :expired-user="router.currentRoute.query.expired_user"
            :message-text="router.currentRoute.query.message"
            :message-variant="router.currentRoute.query.status"
            :token="router.currentRoute.query.token" />
        <LoginIndex
            v-else-if="isConfigLoaded"
            id="login-index"
            :allow-user-creation="config.allow_user_creation"
            :enable-oidc="config.enable_oidc"
            :mailing-join-addr="config.mailing_join_addr"
            :prefer-custos-login="config.prefer_custos_login"
            :redirect="router.currentRoute.query.redirect"
            :registration-warning-message="config.registration_warning_message"
            :server-mail-configured="config.server_mail_configured"
            :session-csrf-token="sessionCsrfToken"
            :show-welcome-with-login="config.show_welcome_with_login"
            :show-reset-link="config.enable_account_interface"
            :terms-url="config.terms_url"
            :welcome-url="config.welcome_url" />
    </div>
</template>
