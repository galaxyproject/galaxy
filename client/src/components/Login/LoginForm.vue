<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <template v-if="!confirmURL">
                <div class="col col-lg-6">
                    <b-alert :show="!!messageText" :variant="messageVariant">
                        {{ messageText }}
                    </b-alert>
                    <b-form id="login" @submit.prevent="submitLogin()">
                        <b-card no-body :header="headerWelcome">
                            <b-card-body>
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <b-form-group :label="labelNameAddress">
                                        <b-form-input v-model="login" name="login" type="text" />
                                    </b-form-group>
                                    <b-form-group :label="labelPassword">
                                        <b-form-input v-model="password" name="password" type="password" />
                                        <b-form-text v-localize>
                                            Forgot password?
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
                                    <external-login :login_page="true" />
                                </div>
                            </b-card-body>
                            <b-card-footer>
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
                                    Registration for this Galaxy instance is disabled. Please contact an administrator
                                    for assistance.
                                </span>
                            </b-card-footer>
                        </b-card>
                    </b-form>
                    <b-modal id="duplicateEmail" ref="duplicateEmail" centered title="Duplicate Email" ok-only>
                        <p>
                            There already exists a user with this email. To associate this external login, you must
                            first be logged in as that existing account.
                        </p>
                        <p>
                            Reminder: Registration and usage of multiple accounts is tracked and such accounts are
                            subject to termination and data deletion. Connect existing account now to avoid possible
                            loss of data.
                        </p>
                    </b-modal>
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
        return {
            login: null,
            password: null,
            url: null,
            messageText: null,
            messageVariant: null,
            headerWelcome: _l("Welcome to Galaxy, please log in"),
            labelNameAddress: _l("Public Name or Email Address"),
            labelPassword: _l("Password"),
        };
    },
    computed: {
        confirmURL() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.has("confirm") && urlParams.get("confirm") == "true";
        },
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
                    } else if (data.redirect) {
                        window.location = encodeURI(data.redirect);
                    } else {
                        window.location = withPrefix("/");
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
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
    },
};
</script>
<style scoped>
.card-body {
    overflow: visible;
}
</style>
