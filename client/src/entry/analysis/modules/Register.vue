<script setup lang="ts">
import { computed } from "vue";

import { getGalaxyInstance } from "@/app";
import { useConfig } from "@/composables/config";

import RegisterIndex from "@/components/Register/RegisterIndex.vue";

const { config, isConfigLoaded } = useConfig();

const sessionCsrfToken = computed(() => {
    return getGalaxyInstance().session_csrf_token;
});
</script>

<template>
    <div class="overflow-auto m-3">
        <RegisterIndex
            v-if="isConfigLoaded"
            id="login-index"
            :disable-local-accounts="config.disable_local_accounts"
            :enable-oidc="config.enable_oidc"
            :mailing-join-addr="config.mailing_join_addr"
            :prefer-custos-login="config.prefer_custos_login"
            :registration-warning-message="config.registration_warning_message"
            :server-mail-configured="config.server_mail_configured"
            :session-csrf-token="sessionCsrfToken"
            :terms-url="config.terms_url" />
    </div>
</template>
