<template>
    <div>
        <template v-if="showLogin">
            <login-form
                :allow-user-creation="allowUserCreation"
                :redirect="redirect"
                :session-csrf-token="sessionCsrfToken"
                :show-welcome-with-login="showWelcomeWithLogin"
                :welcome-url="welcomeUrl"
                @toggle-login="toggleLogin" />
        </template>
        <template v-else>
            <register-form
                :registration-warning-message="registrationWarningMessage"
                :mailing-join-addr="mailingJoinAddr"
                :server-mail-configured="serverMailConfigured"
                :terms-url="termsUrl"
                :enable-oidc="enableOidc"
                :prefer-custos-login="preferCustosLogin"
                :session-csrf-token="sessionCsrfToken"
                :is-admin="isAdmin"
                @toggle-login="toggleLogin" />
        </template>
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
        sessionCsrfToken: {
            type: String,
            default: null,
        },
        showWelcomeWithLogin: {
            type: Boolean,
            required: false,
        },
        welcomeUrl: {
            type: String,
            required: false,
        },
        termsUrl: {
            type: String,
            required: false,
        },
        registrationWarningMessage: {
            type: String,
            required: false,
        },
        mailingJoinAddr: {
            type: String,
            required: false,
        },
        serverMailConfigured: {
            type: Boolean,
            required: false,
        },
        redirect: {
            type: String,
            required: false,
        },
        enableOidc: {
            type: Boolean,
            default: false,
        },
        preferCustosLogin: {
            type: Boolean,
            default: false,
        },
        isAdmin: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            login: true,
        };
    },
    computed: {
        showLogin: function () {
            return this.login;
        },
    },
    methods: {
        toggleLogin: function () {
            this.login = !this.login;
        },
    },
};
</script>
