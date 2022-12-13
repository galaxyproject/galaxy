<template>
    <div>
        <b-alert :show="messageShow" :variant="messageVariant">
            {{ messageText }}
        </b-alert>
        <b-form id="externalLogin">
            <!-- OIDC login-->
            <hr class="my-4" />
            <div v-if="cilogonListShow" class="cilogon">
                <div v-if="login_page">
                    <!--Only Display if CILogon/Custos is configured-->
                    <b-form-group label="Use existing institutional login">
                        <multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cilogon_idps"
                            label="DisplayName"
                            track-by="EntityID">
                        </multiselect>
                    </b-form-group>

                    <b-form-group v-if="login_page">
                        <b-form-checkbox id="remember-idp" v-model="rememberIdp">
                            Remember institution selection
                        </b-form-checkbox>
                    </b-form-group>

                    <b-button v-if="cilogon_enabled" :disabled="selected === null" @click="submitCILogon('cilogon')"
                        >Sign in with Institutional Credentials*</b-button
                    >
                    <!--convert to v-else-if to allow only one or the other. if both enabled, put the one that should be default first-->
                    <b-button
                        v-if="Object.prototype.hasOwnProperty.call(oidc_idps, 'custos')"
                        :disabled="selected === null"
                        @click="submitCILogon('custos')"
                        >Sign in with Custos*</b-button
                    >
                </div>

                <div v-else>
                    <b-button v-if="cilogon_enabled" @click="toggleCILogon('cilogon')"
                        >Sign in with Institutional Credentials*</b-button
                    >

                    <b-button v-if="custos_enabled" @click="toggleCILogon('custos')">Sign in with Custos*</b-button>

                    <b-form-group v-if="toggle_cilogon">
                        <multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cilogon_idps"
                            label="DisplayName"
                            track-by="EntityID">
                        </multiselect>

                        <b-button
                            v-if="toggle_cilogon"
                            :disabled="selected === null"
                            @click="submitCILogon(cilogonOrCustos)"
                            >Login*</b-button
                        >
                    </b-form-group>
                </div>

                <p class="mt-3">
                    <small class="text-muted">
                        * Galaxy uses CILogon via Custos to enable you to log in from this organization. By clicking
                        'Sign In', you agree to the
                        <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy and you agree to
                        share your username, email address, and affiliation with CILogon, Custos, and Galaxy.
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
        </b-form>
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
        login_page: {
            type: Boolean,
            required: false,
        },
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            messageText: null,
            messageVariant: null,
            enable_oidc: galaxy.config.enable_oidc,
            oidc_idps: galaxy.config.oidc,
            cilogon_idps: [],
            selected: null,
            rememberIdp: false,
            cilogonOrCustos: null,
            toggle_cilogon: false,
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
        cilogon_enabled() {
            return Object.prototype.hasOwnProperty.call(this.oidc_idps, "cilogon");
        },
        custos_enabled() {
            return Object.prototype.hasOwnProperty.call(this.oidc_idps, "custos");
        },
    },
    created() {
        this.rememberIdp = this.getIdpPreference() !== null;
        /* Only fetch CILogonIDPs if custos/cilogon configured */
        if (this.cilogonListShow) {
            this.getCILogonIdps();
        }
    },
    methods: {
        toggleCILogon(idp) {
            this.toggle_cilogon = !this.toggle_cilogon;
            this.cilogonOrCustos = this.toggle_cilogon ? idp : null;
        },
        submitOIDCLogin(idp) {
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
            if (this.login_page) {
                this.setIdpPreference();
            }
            axios
                .post(`${rootUrl}authnz/${idp}/login/?idphint=${this.selected.EntityID}`)
                .then((response) => {
                    localStorage.setItem("galaxy-provider", idp);
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
        getCILogonIdps() {
            const rootUrl = getAppRoot();
            axios
                .get(`${rootUrl}authnz/get_cilogon_idps`)
                .then((response) => {
                    this.cilogon_idps = response.data;
                    if (this.cilogon_idps.length == 1) {
                        this.selected = this.cilogon_idps[0];
                    } else {
                        //List is originally sorted by OrganizationName which can be different from DisplayName
                        this.cilogon_idps.sort((a, b) => (a.DisplayName > b.DisplayName ? 1 : -1));
                    }
                })
                .then(() => {
                    if (this.login_page) {
                        const preferredIdp = this.getIdpPreference();
                        if (preferredIdp) {
                            this.selected = this.cilogon_idps.find((idp) => idp.EntityID === preferredIdp);
                        }
                    }
                });
        },
        setIdpPreference() {
            if (this.rememberIdp) {
                localStorage.setItem("galaxy-remembered-idp", this.selected.EntityID);
            } else {
                localStorage.removeItem("galaxy-remembered-idp");
            }
        },
        getIdpPreference() {
            return localStorage.getItem("galaxy-remembered-idp");
        },
    },
};
</script>
<style scoped>
.card-body {
    overflow: visible;
}
</style>
