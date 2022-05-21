<template>
    <div>
        <template v-if="showLogin">
            <login-form :show_welcome_with_login="show_welcome_with_login" :welcome_url="welcome_url" />
        </template>
        <template v-else>
            <register-form
                :registration_warning_message="registration_warning_message"
                :mailing_join_addr="mailing_join_addr"
                :server_mail_configured="server_mail_configured"
                :terms_url="terms_url" />
        </template>
    </div>
</template>
<script>
import LoginForm from "components/login/LoginForm.vue";
import RegisterForm from "components/login/RegisterForm.vue";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    components: {
        loginForm: LoginForm,
        registerForm: RegisterForm,
    },
    props: {
        show_welcome_with_login: {
            type: Boolean,
            required: false,
        },
        welcome_url: {
            type: String,
            required: false,
        },
        terms_url: {
            type: String,
            required: false,
        },
        registration_warning_message: {
            type: String,
            required: false,
        },
        mailing_join_addr: {
            type: String,
            required: false,
        },
        server_mail_configured: {
            type: Boolean,
            required: false,
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
