<script setup lang="ts">
import { useOpenUrl } from "@/composables/openurl";

import RegisterForm from "@/components/Register/RegisterForm.vue";

interface Props {
    disableLocalAccounts?: boolean;
    enableOidc?: boolean;
    mailingJoinAddr?: string;
    preferCustosLogin?: boolean;
    registrationWarningMessage?: string;
    serverMailConfigured?: boolean;
    sessionCsrfToken: string;
    showLoginLink?: boolean;
    termsUrl?: string;
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
            :disable-local-accounts="disableLocalAccounts"
            :enable-oidc="enableOidc"
            :mailing-join-addr="mailingJoinAddr"
            :prefer-custos-login="preferCustosLogin"
            :registration-warning-message="registrationWarningMessage"
            :server-mail-configured="serverMailConfigured"
            :session-csrf-token="sessionCsrfToken"
            :show-login-link="showLoginLink"
            :terms-url="termsUrl"
            @toggle-login="openUrl('/login/start')" />
    </div>
</template>
