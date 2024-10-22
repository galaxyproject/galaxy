<script setup lang="ts">
import { ref } from "vue";

import LoginForm from "@/components/Login/LoginForm.vue";
import RegisterForm from "@/components/Login/RegisterForm.vue";

interface Props {
    sessionCsrfToken: string;
    redirect?: string;
    termsUrl?: string;
    welcomeUrl?: string;
    enableOidc?: boolean;
    showLoginLink?: boolean;
    showResetLink?: boolean;
    mailingJoinAddr?: string;
    allowUserCreation: boolean;
    preferCustosLogin?: boolean;
    serverMailConfigured?: boolean;
    showWelcomeWithLogin?: boolean;
    registrationWarningMessage?: string;
}

withDefaults(defineProps<Props>(), {
    showLoginLink: true,
    showResetLink: true,
    redirect: undefined,
    termsUrl: undefined,
    welcomeUrl: undefined,
    mailingJoinAddr: undefined,
    registrationWarningMessage: undefined,
});

const showLogin = ref(true);

function toggleLogin() {
    showLogin.value = !showLogin.value;
}
</script>

<template>
    <div>
        <LoginForm
            v-if="showLogin"
            :allow-user-creation="allowUserCreation"
            :enable-oidc="enableOidc"
            :redirect="redirect"
            :registration-warning-message="registrationWarningMessage"
            :session-csrf-token="sessionCsrfToken"
            :show-welcome-with-login="showWelcomeWithLogin"
            :terms-url="termsUrl"
            :welcome-url="welcomeUrl"
            :show-reset-link="showResetLink"
            @toggle-login="toggleLogin" />
        <RegisterForm
            v-else
            :enable-oidc="enableOidc"
            :mailing-join-addr="mailingJoinAddr"
            :prefer-custos-login="preferCustosLogin"
            :registration-warning-message="registrationWarningMessage"
            :show-login-link="showLoginLink"
            :server-mail-configured="serverMailConfigured"
            :session-csrf-token="sessionCsrfToken"
            :terms-url="termsUrl"
            @toggle-login="toggleLogin" />
    </div>
</template>
