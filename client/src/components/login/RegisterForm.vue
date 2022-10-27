<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col" :class="{ 'col-lg-6': !isAdmin }">
                <b-alert :show="showRegistrationWarning" variant="info">
                    {{ registrationWarningMessage }}
                </b-alert>
                <b-alert :show="messageShow" :variant="messageVariant">
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
                        <b-card-header v-if="!custosPreferred">Create a Galaxy account</b-card-header>
                        <b-card-header v-else v-b-toggle.accordion-register role="button">
                            Or, register with email
                        </b-card-header>
                        <b-collapse
                            id="accordion-register"
                            :visible="!custosPreferred"
                            role="tabpanel"
                            accordion="registration_acc">
                            <b-card-body>
                                <b-form-group label="Email Address">
                                    <b-form-input v-model="email" name="email" type="text" />
                                </b-form-group>
                                <b-form-group label="Password">
                                    <b-form-input v-model="password" name="password" type="password" />
                                </b-form-group>
                                <b-form-group label="Confirm password">
                                    <b-form-input v-model="confirm" name="confirm" type="password" />
                                </b-form-group>
                                <b-form-group label="Public name">
                                    <b-form-input v-model="username" name="username" type="text" />
                                    <b-form-text
                                        >Your public name is an identifier that will be used to generate addresses for
                                        information you share publicly. Public names must be at least three characters
                                        in length and contain only lower-case letters, numbers, dots, underscores, and
                                        dashes ('.', '_', '-').</b-form-text
                                    >
                                </b-form-group>
                                <b-form-group
                                    v-if="mailingJoinAddr && serverMailConfigured"
                                    label="Subscribe to mailing list">
                                    <input v-model="subscribe" name="subscribe" type="checkbox" />
                                </b-form-group>
                                <b-button name="create" type="submit" :disabled="disableCreate">Create</b-button>
                            </b-card-body>
                        </b-collapse>
                        <b-card-footer v-if="!isAdmin">
                            Already have an account?
                            <a id="login-toggle" href="javascript:void(0)" role="button" @click.prevent="toggleLogin"
                                >Log in here.</a
                            >
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
import { getGalaxyInstance } from "app";
import { safePath } from "utils/redirect";
import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
    },
    props: {
        registrationWarningMessage: {
            type: String,
            default: null,
        },
        serverMailConfigured: {
            type: Boolean,
            default: null,
        },
        mailingJoinAddr: {
            type: String,
            default: null,
        },
        redirect: {
            type: String,
            default: null,
        },
        termsUrl: {
            type: String,
            default: null,
        },
        enableOidc: {
            type: Boolean,
            default: false,
        },
        preferCustosLogin: {
            type: Boolean,
            default: false,
        },
        sessionCsrfToken: {
            type: String,
            default: null,
        },
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            disableCreate: false,
            email: null,
            password: null,
            username: null,
            confirm: null,
            subscribe: null,
            messageText: null,
            messageVariant: null,
            isAdmin: galaxy.user.isAdmin(),
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        },
        showRegistrationWarning() {
            return this.registrationWarningMessage != null;
        },
        custosPreferred() {
            return this.enableOidc && this.preferCustosLogin;
        },
    },
    methods: {
        toggleLogin() {
            this.$emit("toggle-login");
        },
        submit(method) {
            this.disableCreate = true;
            axios
                .post(safePath("/user/create"), {
                    email: this.email,
                    username: this.username,
                    password: this.password,
                    confirm: this.confirm,
                    session_csrf_token: this.sessionCsrfToken,
                })
                .then((response) => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = this.redirect || safePath("/welcome/new");
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
