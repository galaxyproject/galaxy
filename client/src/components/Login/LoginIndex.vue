<template>
    <div>
        <login-form
            v-if="showLogin"
            :allow-user-creation="allowUserCreation"
            :enable-oidc="enableOidc"
            :redirect="redirect"
            :registration-warning-message="registrationWarningMessage"
            :session-csrf-token="sessionCsrfToken"
            :show-welcome-with-login="showWelcomeWithLogin"
            :terms-url="termsUrl"
            :welcome-url="welcomeUrl"
            @toggle-login="toggleLogin" />
        <register-form
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
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";

Vue.use(BootstrapVue);

export default {
    components: {
        LoginForm,
        RegisterForm,
    },
    props: {
        allowUserCreation: {
            type: Boolean,
            required: true,
        },
        enableOidc: {
            type: Boolean,
            default: false,
        },
        mailingJoinAddr: {
            type: String,
            default: null,
        },
        preferCustosLogin: {
            type: Boolean,
            default: false,
        },
        redirect: {
            type: String,
            default: null,
        },
        registrationWarningMessage: {
            type: String,
            default: null,
        },
        showLoginLink: {
            type: Boolean,
            default: true,
        },
        sessionCsrfToken: {
            type: String,
            required: true,
        },
        serverMailConfigured: {
            type: Boolean,
            default: false,
        },
        showWelcomeWithLogin: {
            type: Boolean,
            default: false,
        },
        termsUrl: {
            type: String,
            default: null,
        },
        welcomeUrl: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            showLogin: true,
        };
    },
    methods: {
        toggleLogin() {
            this.showLogin = !this.showLogin;
        },
    },
};
</script>
