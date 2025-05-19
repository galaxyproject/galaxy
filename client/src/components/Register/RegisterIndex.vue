<script setup lang="ts">
import { useOpenUrl } from "@/composables/openurl";

import RegisterForm from "@/components/Register/RegisterForm.vue";

interface Props {
    sessionCsrfToken: string;
    termsUrl?: string;
    enableOidc?: boolean;
    showLoginLink?: boolean;
    mailingJoinAddr?: string;
    preferCustosLogin?: boolean;
    serverMailConfigured?: boolean;
    registrationWarningMessage?: string;
}

withDefaults(defineProps<Props>(), {
    showLoginLink: true,
    termsUrl: undefined,
    mailingJoinAddr: undefined,
    registrationWarningMessage: undefined,
});

const { openUrl } = useOpenUrl();
</script>

<template>
    <div>
        <RegisterForm
            :enable-oidc="enableOidc"
            :mailing-join-addr="mailingJoinAddr"
            :prefer-custos-login="preferCustosLogin"
            :registration-warning-message="registrationWarningMessage"
            :show-login-link="showLoginLink"
            :server-mail-configured="serverMailConfigured"
            :session-csrf-token="sessionCsrfToken"
            :terms-url="termsUrl"
            @toggle-login="openUrl('/login/start')" />
    </div>
</template>
