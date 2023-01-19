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
                <b-form id="confirmation" @submit.prevent="submit()">
                    <b-card no-body header="Confirm new account creation">
                        <b-card-body>
                            <p>Looks like you are about to create a new account!</p>
                            <p>
                                Do you already have a Galaxy account? If so, click
                                <em>'No, go back to login'</em> to log in using your existing username and password to
                                connect this account via <strong>User Preferences</strong>.
                                <a
                                    href="https://galaxyproject.org/authnz/use/oidc/idps/custos/#link-an-existing-galaxy-account"
                                    target="_blank">
                                    More details here.
                                </a>
                            </p>
                            <p>
                                If you wish to continue and create a new account, select
                                <em>'Yes, create new account'</em>.
                            </p>
                            <p>
                                Reminder: Registration and usage of multiple accounts is tracked and such accounts are
                                subject to termination and data deletion on public Galaxy servers. Connect existing
                                account now to continue to use your existing data and avoid possible loss of data.
                            </p>
                            <b-form-group>
                                <b-form-checkbox v-model="termsRead">
                                    I have read and accept these terms to create a new Galaxy account.
                                </b-form-checkbox>
                            </b-form-group>
                            <b-button name="confirm" type="submit" :disabled="!termsRead" @click.prevent="submit">
                                Yes, create new account
                            </b-button>
                            <b-button name="cancel" type="submit" @click.prevent="login">No, go back to login</b-button>
                        </b-card-body>
                        <b-card-footer>
                            Already have an account?
                            <a id="login-toggle" href="javascript:void(0)" role="button" @click.prevent="login">
                                Log in here.
                            </a>
                        </b-card-footer>
                    </b-card>
                </b-form>
            </div>
            <div v-if="termsUrl" class="col">
                <b-embed type="iframe" :src="termsUrlwithRoot" aspect="1by1" />
            </div>
        </div>
    </div>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";

Vue.use(BootstrapVue);

export default {
    props: {
        registrationWarningMessage: {
            type: String,
            default: null,
        },
        termsUrl: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            termsRead: false,
        };
    },
    computed: {
        termsUrlwithRoot() {
            return withPrefix(this.termsUrl);
        },
    },
    methods: {
        login() {
            // set url to redirect user to 3rd party management after login
            this.$emit("setRedirect", "/user/external_ids");
            window.location = withPrefix("/login");
        },
        submit() {
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get("custos_token");
            axios
                .post(withPrefix(`/authnz/custos/create_user?token=${token}`))
                .then((response) => {
                    if (response.data.redirect_uri) {
                        window.location = response.data.redirect_uri;
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
    },
};
</script>
