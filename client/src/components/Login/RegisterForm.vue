<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <b-alert :show="!!registrationWarningMessage" variant="info">
                    {{ registrationWarningMessage }}
                </b-alert>
                <b-alert :show="!!messageText" :variant="messageVariant">
                    {{ messageText }}
                </b-alert>
                <b-form id="registration" @submit.prevent="submit()">
                    <b-card no-body>
                        <!-- OIDC and Custos enabled and prioritized: encourage users to use it instead of local registration -->
                        <span v-if="custosPreferred">
                            <b-card-header v-b-toggle.accordion-oidc role="button">
                                Register using institutional account
                            </b-card-header>
                            <b-collapse id="accordion-oidc" visible role="tabpanel" accordion="registration_acc">
                                <b-card-body>
                                    Create a Galaxy account using an institutional account (e.g.:Google/JHU). This will
                                    redirect you to your institutional login through Custos.
                                    <external-login :login_page="false" />
                                </b-card-body>
                            </b-collapse>
                        </span>
                        <!-- Local Galaxy Registration -->
                        <b-card-header v-if="!custosPreferred" v-localize>Create a Galaxy account</b-card-header>
                        <b-card-header v-else v-localize v-b-toggle.accordion-register role="button">
                            Or, register with email
                        </b-card-header>
                        <b-collapse
                            id="accordion-register"
                            :visible="!custosPreferred"
                            role="tabpanel"
                            accordion="registration_acc">
                            <b-card-body>
                                <b-form-group :label="labelEmailAddress">
                                    <b-form-input v-model="email" name="email" type="text" />
                                </b-form-group>
                                <b-form-group :label="labelPassword">
                                    <b-form-input v-model="password" name="password" type="password" />
                                </b-form-group>
                                <b-form-group :label="labelConfirmPassword">
                                    <b-form-input v-model="confirm" name="confirm" type="password" />
                                </b-form-group>
                                <b-form-group :label="labelPublicName">
                                    <b-form-input v-model="username" name="username" type="text" />
                                    <b-form-text v-localize
                                        >Your public name is an identifier that will be used to generate addresses for
                                        information you share publicly. Public names must be at least three characters
                                        in length and contain only lower-case letters, numbers, dots, underscores, and
                                        dashes ('.', '_', '-').
                                    </b-form-text>
                                </b-form-group>
                                <b-form-group v-if="mailingJoinAddr && serverMailConfigured" :label="labelSubscribe">
                                    <input v-model="subscribe" name="subscribe" type="checkbox" />
                                </b-form-group>
                                <b-button v-localize name="create" type="submit" :disabled="disableCreate"
                                    >Create</b-button
                                >
                            </b-card-body>
                        </b-collapse>
                        <b-card-footer v-if="showLoginLink" v-localize>
                            Already have an account?
                            <a
                                id="login-toggle"
                                v-localize
                                href="javascript:void(0)"
                                role="button"
                                @click.prevent="toggleLogin">
                                Log in here.
                            </a>
                        </b-card-footer>
                    </b-card>
                </b-form>
            </div>
            <div v-if="termsUrl" class="col">
                <b-embed type="iframe" :src="termsUrl" aspect="1by1" />
            </div>
        </div>
    </div>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin";
import _l from "utils/localization";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
    },
    props: {
        enableOidc: {
            type: Boolean,
            default: false,
        },
        showLoginLink: {
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
        serverMailConfigured: {
            type: Boolean,
            default: false,
        },
        sessionCsrfToken: {
            type: String,
            required: true,
        },
        termsUrl: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            disableCreate: false,
            email: null,
            password: null,
            username: null,
            confirm: null,
            subscribe: null,
            messageText: null,
            messageVariant: null,
            labelEmailAddress: _l("Email address"),
            labelPassword: _l("Password"),
            labelConfirmPassword: _l("Confirm password"),
            labelPublicName: _l("Public name"),
            labelSubscribe: _l("Subscribe to mailing list"),
        };
    },
    computed: {
        custosPreferred() {
            return this.enableOidc && this.preferCustosLogin;
        },
    },
    methods: {
        toggleLogin() {
            this.$emit("toggle-login");
        },
        submit() {
            this.disableCreate = true;
            axios
                .post(withPrefix("/user/create"), {
                    email: this.email,
                    username: this.username,
                    password: this.password,
                    confirm: this.confirm,
                    subscribe: this.subscribe,
                    session_csrf_token: this.sessionCsrfToken,
                })
                .then((response) => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = this.redirect || withPrefix("/welcome/new");
                })
                .catch((error) => {
                    this.disableCreate = false;
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Registration failed for an unknown reason.";
                });
        },
    },
};
</script>
