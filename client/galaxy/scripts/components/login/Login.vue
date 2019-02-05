<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
                <b-form id="login" @submit.prevent="submit()">
                    <b-card header="Welcome to Galaxy, please log in">
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
                        <b-button type="submit">Login</b-button>
                    </b-card>
                </b-form>
            </div>
            <div :show="showOIDC" class="col col-lg-6">
                <div class="card">
                    <div class="card-header">OR</div>
                    <form name="oidc" id="oidc" action="/authnz/Google/login" method="post" >
                        <div class="form-row">
                            <input type="submit" value="Login with Google"/>
                        </div>
                    </form>
                </div>
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
        let Galaxy = getGalaxyInstance();
        return {
            login: null,
            password: null,
            url: null,
            provider: null,
            messageText: null,
            messageVariant: null,
            redirect: Galaxy.params.redirect
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        },
        showOIDC() {
            let Galaxy = getGalaxyInstance();
            return Galaxy.config.enable_oidc == true;
        }
    },
    methods: {
        submit: function(method) {
            let rootUrl = getAppRoot();
            let data = { login: this.login, password: this.password, redirect: this.redirect };
            axios
                .post(`${rootUrl}user/login`, data)
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
