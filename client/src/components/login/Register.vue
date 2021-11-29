<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col" :class="{ 'col-lg-6': !isAdmin }">
                <b-alert v-html="registration_warning_message" :show="showRegistrationWarning" variant="info">
                </b-alert>
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
                <b-form id="registration" @submit.prevent="submit()">
                    <b-card no-body header="Create a Galaxy account">
                        <b-card-body>
                            <b-form-group label="Email Address">
                                <b-form-input name="email" type="text" v-model="email" />
                            </b-form-group>
                            <b-form-group label="Password">
                                <b-form-input name="password" type="password" v-model="password" />
                            </b-form-group>
                            <b-form-group label="Confirm password">
                                <b-form-input name="confirm" type="password" v-model="confirm" />
                            </b-form-group>
                            <b-form-group label="Public name">
                                <b-form-input name="username" type="text" v-model="username" />
                                <b-form-text
                                    >Your public name is an identifier that will be used to generate addresses for
                                    information you share publicly. Public names must be at least three characters in
                                    length and contain only lower-case letters, numbers, dots, underscores, and dashes
                                    ('.', '_', '-').</b-form-text
                                >
                            </b-form-group>
                            <b-form-group
                                v-if="mailing_join_addr && server_mail_configured"
                                label="Subscribe to mailing list">
                                <input name="subscribe" type="checkbox" v-model="subscribe" />
                            </b-form-group>
                            <b-button name="create" type="submit" :disabled="disableCreate">Create</b-button>
                        </b-card-body>
                        <b-card-footer v-if="!isAdmin">
                            Already have an account?
                            <a id="login-toggle" href="javascript:void(0)" role="button" @click.prevent="toggleLogin"
                                >Log in here.</a
                            >
                        </b-card-footer>
                    </b-card>
                </b-form>
            </div>
            <div v-if="terms_url" class="col">
                <b-embed type="iframe" :src="terms_url" aspect="1by1" />
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

Vue.use(BootstrapVue);

export default {
    props: {
        registration_warning_message: {
            type: String,
            required: false,
        },
        server_mail_configured: {
            type: Boolean,
            required: false,
        },
        mailing_join_addr: {
            type: String,
            required: false,
        },
        redirect: {
            type: String,
            required: false,
        },
        terms_url: {
            type: String,
            required: false,
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
            session_csrf_token: galaxy.session_csrf_token,
            isAdmin: galaxy.user.isAdmin(),
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        },
        showRegistrationWarning() {
            return this.registration_warning_message != null;
        },
    },
    methods: {
        toggleLogin: function () {
            if (this.$root.toggleLogin) {
                this.$root.toggleLogin();
            }
        },
        submit: function (method) {
            this.disableCreate = true;
            const rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}user/create`, this.$data)
                .then((response) => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = this.redirect || `${rootUrl}welcome/new`;
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
