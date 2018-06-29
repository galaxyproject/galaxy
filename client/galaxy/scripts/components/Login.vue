<template>
    <b-form @submit="submit">
        <b-card title="Welcome to Galaxy, please log in here">
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
            console.debug("HANDLE LOGIN!");
        }
    }
};
</script>
