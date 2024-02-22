<template>
    <div>
        <b-alert :show="messageShow" :variant="messageVariant">
            {{ messageText }}
        </b-alert>
        <b-form id="externalLogin">
            <!-- OIDC login-->
            <hr v-if="!indexedView" class="my-4" />
            <div v-if="cilogonListShow" class="cilogon">
                <!-- If we are in non indexed, typical login page OR indexed view and either custos/cilogon key -->
                <div v-if="login_page && (!indexedView || providerKey === 'custos' || providerKey === 'cilogon')">
                    <!--Only Display if CILogon/Custos is configured-->
                    <b-form-group :label="!indexedView ? 'Use existing institutional login' : null">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cilogon_idps"
                            label="DisplayName"
                            track-by="EntityID">
                        </Multiselect>
                    </b-form-group>

                    <b-form-group v-if="login_page">
                        <b-form-checkbox id="remember-idp" v-model="rememberIdp">
                            Remember institution selection
                        </b-form-checkbox>
                    </b-form-group>

                    <b-button
                        v-if="cilogon_enabled && (!indexedView || providerKey === 'cilogon')"
                        :disabled="loading || selected === null"
                        @click="submitCILogon('cilogon')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Institutional Credentials*</span>
                    </b-button>
                    <!--convert to v-else-if to allow only one or the other. if both enabled, put the one that should be default first-->
                    <b-button
                        v-if="
                            Object.prototype.hasOwnProperty.call(oidc_idps, 'custos') &&
                            (!indexedView || providerKey === 'custos')
                        "
                        :disabled="loading || selected === null"
                        @click="submitCILogon('custos')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Custos*</span>
                    </b-button>
                </div>

                <div v-else-if="!login_page">
                    <b-button v-if="cilogon_enabled" @click="toggleCILogon('cilogon')">
                        Sign in with Institutional Credentials*
                    </b-button>

                    <b-button v-if="custos_enabled" @click="toggleCILogon('custos')">Sign in with Custos*</b-button>

                    <b-form-group v-if="toggle_cilogon">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cilogon_idps"
                            label="DisplayName"
                            track-by="EntityID">
                        </Multiselect>

                        <b-button
                            v-if="toggle_cilogon"
                            :disabled="loading || selected === null"
                            @click="submitCILogon(cilogonOrCustos)">
                            Login*
                        </b-button>
                    </b-form-group>
                </div>

                <p v-if="!indexedView" class="mt-3">
                    <small class="text-muted">
                        * Galaxy uses CILogon via Custos to enable you to log in from this organization. By clicking
                        'Sign In', you agree to the
                        <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy and you agree to
                        share your username, email address, and affiliation with CILogon, Custos, and Galaxy.
                    </small>
                </p>
            </div>

            <span v-if="!indexedView">
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
            </span>
            <div v-else-if="filtered_oidc_idps[providerKey]">
                <span v-if="filtered_oidc_idps[providerKey]['icon']">
                    <b-button variant="link" class="d-block mt-3" @click="submitOIDCLogin(providerKey)">
                        <img :src="filtered_oidc_idps[providerKey]['icon']" height="45" :alt="idp" />
                    </b-button>
                </span>
                <span v-else>
                    <b-button class="d-block mt-3" @click="submitOIDCLogin(providerKey)">
                        <i :class="oidc_idps[providerKey]" />
                        Sign in with
                        {{ providerKey.charAt(0).toUpperCase() + providerKey.slice(1) }}
                    </b-button>
                </span>
            </div>
        </b-form>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload";
import Vue from "vue";
import Multiselect from "vue-multiselect";

Vue.use(BootstrapVue);

export default {
    components: {
        Multiselect,
        LoadingSpan,
    },
    props: {
        login_page: {
            type: Boolean,
            required: false,
        },
        exclude_idps: {
            type: Array,
            required: false,
        },
        /** A version of `ExternalLogin` where only one provider is shown
         * at a time and the provider is specified by `providerKey`
         */
        indexedView: {
            type: Boolean,
            required: false,
        },
        /** If `indexedView` is true, the provider to show */
        providerKey: {
            type: String,
            default: null,
        },
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            loading: false,
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
            const exclude = ["cilogon", "custos"].concat(this.exclude_idps);
            const filtered = Object.assign({}, this.oidc_idps);
            exclude.forEach((idp) => {
                delete filtered[idp];
            });
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
            this.loading = true;
            axios
                .post(`${rootUrl}authnz/${idp}/login`)
                .then((response) => {
                    this.loading = false;
                    if (response.data.redirect_uri) {
                        window.location = response.data.redirect_uri;
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
                    this.loading = false;
                });
        },
        submitCILogon(idp) {
            const rootUrl = getAppRoot();
            if (this.login_page) {
                this.setIdpPreference();
            }
            this.loading = true;
            axios
                .post(`${rootUrl}authnz/${idp}/login/?idphint=${this.selected.EntityID}`)
                .then((response) => {
                    this.loading = false;
                    localStorage.setItem("galaxy-provider", idp);
                    if (response.data.redirect_uri) {
                        window.location = response.data.redirect_uri;
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;

                    this.messageText = message || "Login failed for an unknown reason.";
                    this.loading = false;
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
