<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <template v-if="!confirmURL">
                <div class="col col-lg-6">
                    <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
                    <b-form id="login" @submit.prevent="submitGalaxyLogin()">
                        <b-card no-body header="Welcome to Galaxy, please log in">
                            <b-card-body>
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <b-form-group label="Public Name or Email Address">
                                        <b-form-input v-model="login" name="login" type="text" />
                                    </b-form-group>
                                    <b-form-group label="Password">
                                        <b-form-input v-model="password" name="password" type="password" />
                                        <b-form-text>
                                            Forgot password?
                                            <a href="javascript:void(0)" role="button" @click="reset"
                                                >Click here to reset your password.</a
                                            >
                                        </b-form-text>
                                    </b-form-group>
                                    <b-button name="login" type="submit">Login</b-button>
                                </div>
                                <div v-if="enable_oidc">
                                    <!-- OIDC login-->
                                    <external-login :login_page="true" />
                                </div>
                            </b-card-body>
                            <b-card-footer>
                                Don't have an account?
                                <span v-if="allowUserCreation">
                                    <a
                                        id="register-toggle"
                                        href="javascript:void(0)"
                                        role="button"
                                        @click.prevent="toggleLogin"
                                        >Register here.</a
                                    >
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
                        -->
                    </b-modal>
                </div>
            </template>

            <template v-else>
                <new-user-confirmation @setRedirect="setRedirect" />
            </template>

            <div v-if="show_welcome_with_login" class="col">
                <b-embed type="iframe" :src="welcome_url" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import NewUserConfirmation from "components/login/NewUserConfirmation.vue";
import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
        NewUserConfirmation,
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
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            login: null,
            password: null,
            url: null,
            messageText: null,
            messageVariant: null,
            allowUserCreation: galaxy.config.allow_user_creation,
            redirect: galaxy.params.redirect,
            session_csrf_token: galaxy.session_csrf_token,
            enable_oidc: galaxy.config.enable_oidc,
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        },
        confirmURL() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.has("confirm") && urlParams.get("confirm") == "true";
        },
    },
    methods: {
        toggleLogin() {
            if (this.$root.toggleLogin) {
                this.$root.toggleLogin();
            }
        },
        submitGalaxyLogin(method) {
            if (localStorage.getItem("redirect_url")) {
                this.redirect = localStorage.getItem("redirect_url");
            }
            const rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}user/login`, this.$data)
                .then((response) => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    if (response.data.expired_user) {
                        window.location = `${rootUrl}root/login?expired_user=${response.data.expired_user}`;
                    } else if (response.data.redirect) {
                        window.location = encodeURI(response.data.redirect);
                    } else {
                        window.location = `${rootUrl}`;
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
        reset(ev) {
            const rootUrl = getAppRoot();
            ev.preventDefault();
            axios
                .post(`${rootUrl}user/reset_password`, { email: this.login })
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
