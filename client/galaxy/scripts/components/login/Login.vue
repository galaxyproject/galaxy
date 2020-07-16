<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
                <b-form id="login" @submit.prevent="submitGalaxyLogin()">
                    <b-card no-body header="Welcome to Galaxy, please log in">
                        <b-card-body>
                            <div>
                                <!-- standard internal galaxy login -->
                                <b-form-group label="Public Name or Email Address">
                                    <b-form-input name="login" type="text" v-model="login" />
                                </b-form-group>
                                <b-form-group label="Password">
                                    <b-form-input name="password" type="password" v-model="password" />
                                    <b-form-text>
                                        Forgot password?
                                        <a @click="reset" href="javascript:void(0)" role="button"
                                            >Click here to reset your password.</a
                                        >
                                    </b-form-text>
                                </b-form-group>
                                <b-button name="login" type="submit">Login</b-button>
                            </div>
                            <div v-if="enable_oidc">
                                <!-- OIDC login-->
                                <hr class="my-4" />
                                <div class="cilogon" v-if="cilogonListShow">
                                    <!--Only Display if CILogon/Custos is configured-->
                                    <b-form-group label="Use existing institutional login">
                                        <multiselect
                                            placeholder="Select your institution"
                                            v-model="selected"
                                            :options="cilogon_idps"
                                            label="DisplayName"
                                            track-by="EntityID"
                                        >
                                        </multiselect>
                                    </b-form-group>

                                    <b-button
                                        v-if="Object.prototype.hasOwnProperty.call(oidc_idps, 'cilogon')"
                                        @click="submitCILogon('cilogon')"
                                        :disabled="selected === null"
                                        >Sign in with Institutional Credentials*</b-button
                                    >
                                    <!--convert to v-else-if to allow only one or the other. if both enabled, put the one that should be default first-->
                                    <b-button
                                        v-if="Object.prototype.hasOwnProperty.call(oidc_idps, 'custos')"
                                        @click="submitCILogon('custos')"
                                        :disabled="selected === null"
                                        >Sign in with Custos *</b-button
                                    >

                                    <p class="mt-3">
                                        <small class="text-muted">
                                            * Galaxy uses CILogon via Custos to enable you to log in from this
                                            organization. By clicking 'Sign In', you agree to the
                                            <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy
                                            and you agree to share your username, email address, and affiliation with
                                            CILogon, Custos, and Galaxy.
                                        </small>
                                    </p>
                                </div>

                                <div v-for="(idp_info, idp) in filtered_oidc_idps" :key="idp" class="m-1">
                                    <span v-if="idp_info['icon']">
                                        <b-button variant="link" class="d-block mt-3" @click="submitOIDCLogin(idp)">
                                            <img :src="idp_info['icon']" height="45" :alt="idp" />
                                        </b-button>
                                    </span>
                                    <span v-else>
                                        <b-button class="d-block mt-3" @click="submitOIDCLogin(idp)">
                                            <i :class="oidc_idps[idp]" />
                                            Sign in with
                                            {{ idp.charAt(0).toUpperCase() + idp.slice(1) }}
                                        </b-button>
                                    </span>
                                </div>
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
                                Registration for this Galaxy instance is disabled. Please contact an administrator for
                                assistance.
                            </span>
                        </b-card-footer>
                    </b-card>
                </b-form>

                <b-modal centered id="duplicateEmail" ref="duplicateEmail" title="Duplicate Email" ok-only>
                    <p>
                        There already exists a user with this email. To associate this external login, you must first be
                        logged in as that existing account.
                    </p>

                    <p>
                        Reminder: Registration and usage of multiple accounts is tracked and such accounts are subject
                        to termination and data deletion. Connect existing account now to avoid possible loss of data.
                    </p>
                    -->
                </b-modal>
            </div>

            <div v-if="show_welcome_with_login" class="col">
                <b-embed type="iframe" :src="welcome_url" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import Multiselect from "vue-multiselect";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

Vue.use(BootstrapVue);

export default {
    components: {
        Multiselect,
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
            provider: null,
            messageText: null,
            messageVariant: null,
            allowUserCreation: galaxy.config.allow_user_creation,
            redirect: galaxy.params.redirect,
            session_csrf_token: galaxy.session_csrf_token,
            enable_oidc: galaxy.config.enable_oidc,
            oidc_idps: galaxy.config.oidc,
            cilogon_idps: [],
            selected: null,
        };
    },
    computed: {
        filtered_oidc_idps() {
            const filtered = Object.assign({}, this.oidc_idps);
            delete filtered.custos;
            delete filtered.cilogon;
            return filtered;
        },
        cilogonListShow() {
            return (
                Object.prototype.hasOwnProperty.call(this.oidc_idps, "cilogon") ||
                Object.prototype.hasOwnProperty.call(this.oidc_idps, "custos")
            );
        },
        messageShow() {
            return this.messageText != null;
        },
    },
    methods: {
        toggleLogin: function () {
            if (this.$root.toggleLogin) {
                this.$root.toggleLogin();
            }
        },
        submitGalaxyLogin: function (method) {
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
        submitOIDCLogin: function (idp) {
            const rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}authnz/${idp}/login`)
                .then((response) => {
                    if (response.data.redirect_uri) {
                        window.location = response.data.redirect_uri;
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
                });
        },
        submitCILogon(idp) {
            const rootUrl = getAppRoot();

            axios
                .post(`${rootUrl}authnz/${idp}/login/?idphint=${this.selected.EntityID}`)
                .then((response) => {
                    if (response.data.redirect_uri) {
                        window.location = response.data.redirect_uri;
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;

                    this.messageText = message || "Login failed for an unknown reason.";
                })
                .finally(() => {
                    var urlParams = new URLSearchParams(window.location.search);

                    if (urlParams.has("message") && urlParams.get("message") == "Duplicate Email") {
                        this.$refs.duplicateEmail.show();
                    }
                });
        },
        reset: function (ev) {
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
        getCILogonIdps() {
            const rootUrl = getAppRoot();

            axios.get(`${rootUrl}authnz/get_cilogon_idps`).then((response) => {
                this.cilogon_idps = response.data;
                //List is originally sorted by OrganizationName which can be different from DisplayName
                this.cilogon_idps.sort((a, b) => (a.DisplayName > b.DisplayName ? 1 : -1));
            });
        },
    },
    created() {
        this.getCILogonIdps();
    },
};
</script>
<style scoped>
.card-body {
    overflow: visible;
}
</style>
