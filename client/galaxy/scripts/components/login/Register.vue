<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <b-alert :show="registration_warning_message" variant="danger">
                    {{ registration_warning_message }}
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
                            <b-form-group v-if="mailing_join_addr && smtp_server" label="Subscribe to mailing list">
                                <input name="subscribe" type="checkbox" v-model="subscribe" />
                            </b-form-group>
                            <b-button name="create" type="submit">Create</b-button>
                        </b-card-body>
                        <b-card-footer>
                            Already have an account?
                            <a id="login-toggle" href="#" @click.prevent="toggleLogin">Log in here.</a>
                        </b-card-footer>
                    </b-card>
                </b-form>
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
            required: false
        },
        smtp_server: {
            type: String,
            required: false
        },
        mailing_join_addr: {
            type: String,
            required: false
        },
        redirect: {
            type: String,
            required: false
        }
    },
    data() {
        let galaxy = getGalaxyInstance();
        return {
            email: null,
            password: null,
            username: null,
            confirm: null,
            subscribe: null,
            messageText: null,
            messageVariant: null,
            session_csrf_token: galaxy.session_csrf_token
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        }
    },
    methods: {
        toggleLogin: function() {
            if (this.$root.toggleLogin) {
                this.$root.toggleLogin();
            }
        },
        submit: function(method) {
            let rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}user/create`, this.$data)
                .then(response => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = this.redirect || rootUrl;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Registration failed for an unknown reason.";
                });
        }
    }
};
</script>
