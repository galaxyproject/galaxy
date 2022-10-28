<template>
    <div>
        <login-form
            v-if="showLogin"
            :allow-user-creation="allowUserCreation"
            :enable-oidc="enableOidc"
            :is-admin="isAdmin"
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
            :is-admin="isAdmin"
            :mailing-join-addr="mailingJoinAddr"
            :prefer-custos-login="preferCustosLogin"
            :registration-warning-message="registrationWarningMessage"
            :server-mail-configured="serverMailConfigured"
            :session-csrf-token="sessionCsrfToken"
            :terms-url="termsUrl"
            @toggle-login="toggleLogin" />
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import LoginForm from "components/login/LoginForm";
import RegisterForm from "components/login/RegisterForm";

Vue.use(BootstrapVue);

export default {
    components: {
        LoginForm,
        RegisterForm,
    },
    props: {
        allowUserCreation: {
            type: Boolean,
            default: false,
        },
        enableOidc: {
            type: Boolean,
            default: false,
        },
        isAdmin: {
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
        sessionCsrfToken: {
            type: String,
            default: null,
        },
        serverMailConfigured: {
            type: Boolean,
            required: false,
        },
        showWelcomeWithLogin: {
            type: Boolean,
            required: false,
        },
        termsUrl: {
            type: String,
            required: false,
        },
        welcomeUrl: {
            type: String,
            required: false,
        },
    },
    data() {
        return {
            login: true,
        };
    },
    computed: {
        showLogin() {
            return this.login;
        },
    },
    methods: {
        toggleLogin() {
            this.login = !this.login;
        },
    },
};
</script>
