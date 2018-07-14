<template>
    <b-form @submit="submit">
        <b-card header="Welcome to Galaxy, please log in">
            <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
            <b-form-group label="Username or Email Address">
                <b-form-input type="text" v-model="username"/>
            </b-form-group>
            <b-form-group label="Password">
                <b-form-input type="password" v-model="password"/>
            </b-form-group>
            <b-button type="submit">Login</b-button>
        </b-card>
    </b-form>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    data() {
        return {
            username: null,
            password: null,
            errorMessage: null
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        }
    },
    methods: {
        submit: function(ev) {
            ev.preventDefault();
            axios
                .post(`${Galaxy.root}user/login`, {username: this.username, password: this.password})
                .then(response => {
                    window.location = `${Galaxy.root}`;
                })
                .catch(error => {
                    let message = error.response.data && error.response.data.err_msg;
                    this.errorMessage = message || "Login failed for unkown reason.";
                });
        }
    }
};
</script>
