<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <template v-if="!confirmURL">
                <div class="col col-lg-6">
                    <b-alert :show="!!messageText" :variant="messageVariant">
                        <span v-html="messageText" />
                    </b-alert>
                    <b-alert :show="!!connectExternalProvider" variant="info">
                        There already exists a user with the email <i>{{ connectExternalEmail }}</i
                        >. In order to associate this account with <i>{{ connectExternalLabel }}</i
                        >, you must first login to your existing account.
                    </b-alert>
                    <b-form id="login" @submit.prevent="submitLogin()">
                        <b-card no-body>
                            <b-card-header v-if="!connectExternalProvider">
                                <span>{{ headerWelcome }}</span>
                            </b-card-header>
                            <b-card-body>
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <b-form-group :label="labelNameAddress" label-for="login-form-name">
                                        <b-form-input
                                            v-if="!connectExternalProvider"
                                            id="login-form-name"
                                            v-model="login"
                                            name="login"
                                            type="text" />
                                        <b-form-input
                                            v-else
                                            id="login-form-name"
                                            disabled
                                            :value="connectExternalEmail"
                                            name="login"
                                            type="text" />
                                    </b-form-group>
                                    <b-form-group :label="labelPassword" label-for="login-form-password">
                                        <b-form-input
                                            id="login-form-password"
                                            v-model="password"
                                            name="password"
                                            type="password" />
                                        <b-form-text>
                                            <span v-localize>Forgot password?</span>
                                            <a
                                                v-localize
                                                href="javascript:void(0)"
                                                role="button"
                                                @click.prevent="resetLogin">
                                                Click here to reset your password.
                                            </a>
                                        </b-form-text>
                                    </b-form-group>
                                    <b-button v-localize name="login" type="submit">Login</b-button>
                                </div>
                                <div v-if="enableOidc">
                                    <!-- OIDC login-->
                                    <external-login :login_page="true" :exclude_idps="[connectExternalProvider]" />
                                </div>
                            </b-card-body>
                            <b-card-footer>
                                <span v-if="!connectExternalProvider">
                                    Don't have an account?
                                    <span v-if="allowUserCreation">
                                        <a
                                            id="register-toggle"
                                            v-localize
                                            href="javascript:void(0)"
                                            role="button"
                                            @click.prevent="toggleLogin">
                                            Register here.
                                        </a>
                                    </span>
                                    <span v-else>
                                        Registration for this Galaxy instance is disabled. Please contact an
                                        administrator for assistance.
                                    </span>
                                </span>
                                <span v-else>
                                    Do not wish to connect to an external provider?
                                    <a href="javascript:void(0)" role="button" @click.prevent="returnToLogin">
                                        Return to login here.
                                    </a>
                                </span>
                            </b-card-footer>
                        </b-card>
                    </b-form>
                </div>
            </template>
            <template v-else>
                <new-user-confirmation
                    :registration-warning-message="registrationWarningMessage"
                    :terms-url="termsUrl"
                    @setRedirect="setRedirect" />
            </template>
            <div v-if="showWelcomeWithLogin" class="col">
                <b-embed type="iframe" :src="welcomeUrlWithRoot" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import NewUserConfirmation from "./NewUserConfirmation";
import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin";
import _l from "utils/localization";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
        NewUserConfirmation,
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
            required: true,
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
        const urlParams = new URLSearchParams(window.location.search);
        return {
            login: null,
            password: null,
            url: null,
            messageText: null,
            messageVariant: null,
            headerWelcome: _l("Welcome to Galaxy, please log in"),
            labelNameAddress: _l("Public Name or Email Address"),
            labelPassword: _l("Password"),
            confirmURL: urlParams.has("confirm") && urlParams.get("confirm") == "true",
            connectExternalEmail: urlParams.get("connect_external_email"),
            connectExternalProvider: urlParams.get("connect_external_provider"),
            connectExternalLabel: urlParams.get("connect_external_label"),
        };
    },
    computed: {
        welcomeUrlWithRoot() {
            return withPrefix(this.welcomeUrl);
        },
    },
    methods: {
        toggleLogin() {
            this.$emit("toggle-login");
        },
        submitLogin() {
            let redirect = this.redirect;
            if (this.connectExternalEmail) {
                this.login = this.connectExternalEmail;
            }
            if (localStorage.getItem("redirect_url")) {
                redirect = localStorage.getItem("redirect_url");
            }
            axios
                .post(withPrefix("/user/login"), {
                    login: this.login,
                    password: this.password,
                    redirect: redirect,
                    session_csrf_token: this.sessionCsrfToken,
                })
                .then(({ data }) => {
                    if (data.message && data.status) {
                        alert(data.message);
                    }
                    if (data.expired_user) {
                        window.location = withPrefix(`/root/login?expired_user=${data.expired_user}`);
                    } else if (this.connectExternalProvider) {
                        window.location = withPrefix("/user/external_ids?connect_external=true");
                    } else if (data.redirect) {
                        window.location = encodeURI(data.redirect);
                    } else {
                        window.location = withPrefix("/");
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response && error.response.data && error.response.data.err_msg;
                    if (this.connectExternalProvider && message && message.toLowerCase().includes("invalid")) {
                        this.messageText =
                            message + " Try logging in to the existing account through an external provider below.";
                    } else {
                        this.messageText = message || "Login failed for an unknown reason.";
                    }
                });
        },
        setRedirect(url) {
            localStorage.setItem("redirect_url", url);
        },
        resetLogin() {
            axios
                .post(withPrefix("/user/reset_password"), { email: this.login })
                .then((response) => {
                    this.messageVariant = "info";
                    this.messageText = response.data.message;
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Password reset failed for an unknown reason.";
                });
        },
        returnToLogin() {
            window.location = withPrefix("/login/start");
        },
    },
};
</script>
<style scoped>
.card-body {
    overflow: visible;
}
</style>
