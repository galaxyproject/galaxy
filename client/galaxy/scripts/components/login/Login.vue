<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
                <b-form id="login" @submit.prevent="submitGalaxyLogin()">
                    <b-card no-body header="Welcome to Galaxy, please log in">
                        <b-card-body>
                            <b-form-group label="Username or Email Address">
                                <b-form-input name="login" type="text" v-model="login" />
                            </b-form-group>
                            <b-form-group label="Password">
                                <b-form-input name="password" type="password" v-model="password" />
                                <b-form-text
                                    >Forgot password? Click here to <a @click="reset" href="#">reset</a> your
                                    password.</b-form-text
                                >
                            </b-form-group>
                            <b-button name="login" type="submit">Login</b-button>
                        </b-card-body>
                        <b-card-footer>
                            Don't have an account?
                            <a id="register-toggle" href="#" @click.prevent="toggleLogin">Register here.</a>
                        </b-card-footer>
                    </b-card>
                </b-form>
                <b-button v-if="enable_oidc" class="mt-3" @click="submitOIDCLogin()">
                    <icon class="fa fa-google" /> Sign in with Google
                </b-button>
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
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

Vue.use(BootstrapVue);

export default {
    props: {
        show_welcome_with_login: {
            type: Boolean,
            required: false
        },
        welcome_url: {
            type: String,
            required: false
        }
    },
    data() {
        let galaxy = getGalaxyInstance();
        return {
            login: null,
            password: null,
            url: null,
            provider: null,
            messageText: null,
            messageVariant: null,
            redirect: galaxy.params.redirect,
            session_csrf_token: galaxy.session_csrf_token,
            enable_oidc: galaxy.config.enable_oidc
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
        submitGalaxyLogin: function(method) {
            let rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}user/login`, this.$data)
                .then(response => {
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
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
                });
        },
        submitOIDCLogin: function(method) {
            let rootUrl = getAppRoot();
            axios
                .post(`${rootUrl}authnz/google/login`)
                .then(response => {
                    if (response.data.redirect_uri) {
                        window.location = encodeURI(response.data.redirect_uri);
                    }
                    // Else do something intelligent or maybe throw an error -- what else does this endpoint possibly return?
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
                });
        },
        reset: function(ev) {
            let rootUrl = getAppRoot();
            ev.preventDefault();
            axios
                .post(`${rootUrl}user/reset_password`, { email: this.login })
                .then(response => {
                    this.messageVariant = "info";
                    this.messageText = response.data.message;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Password reset failed for an unknown reason.";
                });
        }
    }
};
</script>
