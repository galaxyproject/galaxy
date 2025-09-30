<script setup lang="ts">
import LoginForm from "@/components/Login/LoginForm.vue";

interface Props {
    sessionCsrfToken: string;
    redirect?: string;
    termsUrl?: string;
    welcomeUrl?: string;
    enableOidc?: boolean;
    showResetLink?: boolean;
    allowUserCreation: boolean;
    showWelcomeWithLogin?: boolean;
    registrationWarningMessage?: string;
    disableLocalAccounts?: boolean;
}

withDefaults(defineProps<Props>(), {
    showResetLink: true,
    redirect: undefined,
    termsUrl: undefined,
    welcomeUrl: undefined,
    registrationWarningMessage: undefined,
    disableLocalAccounts: false,
});
</script>

<template>
    <div>
        <LoginForm
            :allow-user-creation="allowUserCreation"
            :disable-local-accounts="disableLocalAccounts"
            :enable-oidc="enableOidc"
            :redirect="redirect"
            :registration-warning-message="registrationWarningMessage"
            :session-csrf-token="sessionCsrfToken"
            :show-welcome-with-login="showWelcomeWithLogin"
            :terms-url="termsUrl"
            :welcome-url="welcomeUrl"
            :show-reset-link="showResetLink" />
    </div>
</template>
