<template>
    <section class="external-id">
        <header>
            <b-alert
                dismissible
                fade
                variant="warning"
                :show="errorMessage !== null"
                @dismissed="errorMessage = null"
                >{{ errorMessage }}</b-alert
            >

            <hgroup class="external-id-title">
                <h1>Manage External Identities</h1>
            </hgroup>

            <p>
                Users with existing Galaxy user accounts (e.g., via Galaxy username and password) can associate their
                account with their 3rd party identities. For instance, if a user associates their Galaxy account with
                their Google account, then they can login to Galaxy either using their Galaxy username and password, or
                their Google account. Whichever method they use they will be assuming same Galaxy user account, hence
                having access to the same histories, workflows, datasets, libraries, etc.
            </p>

            <p>
                See more information, including a list of supported identity providers,
                <a href="https://galaxyproject.org/authnz/use/oidc/">here</a>.
            </p>
        </header>

        <div class="external-subheading" v-if="items.length">
            <h3>Connected External Identities</h3>
            <b-button
                @click="onDisconnect(item)"
                aria-label="Disconnect External Identity"
                title="Disconnect External Identity"
                v-for="item in items"
                :key="item.provider"
                class="d-block mt-3"
            >
                Disconnect {{ item.provider.charAt(0).toUpperCase() + item.provider.slice(1) }} - {{ item.email }}
            </b-button>

            <b-modal
                centered
                id="disconnectIDModal"
                ref="deleteModal"
                title="Disconnect Identity?"
                size="sm"
                @ok="disconnectID"
                @cancel="doomedItem = null"
            ></b-modal>

            <b-modal
                centered
                id="disconnectAndResetModal"
                ref="deleteAndResetModal"
                title="Deleting last external identity"
                @ok="disconnectAndReset"
                @cancel="doomedItem = null"
            >
                <p>
                    This is your only defined external identity. If you delete this identity, you will be logged out. To
                    log back in you will need to use a password associated with your account, or reconnect to this third
                    party identity. If you don't know your Galaxy user password, you can reset it or contact an
                    administrator for help.
                </p>
            </b-modal>

            <b-alert
                dismissible
                fade
                variant="warning"
                :show="errorMessage !== null"
                @dismissed="errorMessage = null"
                >{{ errorMessage }}</b-alert
            >
        </div>

        <div class="external-subheading" v-if="enable_oidc">
            <h3>Connect Other External Identities</h3>
            <b-button
                v-if="Object.prototype.hasOwnProperty.call(oidc_idps, 'cilogon')"
                @click="toggleCILogon('cilogon')"
                >Sign in with Institutional Credentials*</b-button
            >
            
            <b-button
                v-if="Object.prototype.hasOwnProperty.call(oidc_idps, 'custos')"
                @click="toggleCILogon('custos')"
                >Sign in with Custos*</b-button
            >

            <div v-if="toggle_cilogon">
                <!-- OIDC login-->
                <hr class="my-4" />
                <div class="cilogon">
                    <!--Only Display if CILogon/Custos is configured-->
                    <b-form-group>
                        <multiselect
                            placeholder="Select your institution"
                            v-model="selected"
                            :options="cilogon_idps"
                            label="DisplayName"
                            track-by="EntityID"
                        >
                        </multiselect>
                    </b-form-group>

                    <b-button class="d-block mt-3" @click="submitOIDCLogin(cilogonOrCustos)" :disabled="selected === null">
                        Login
                    </b-button>
                    
                    <p class="mt-3">
                        <small class="text-muted">
                            * Galaxy uses CILogon via Custos to enable you to log in from this
                            organization. By clicking 'Sign In', you agree to the
                            <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy
                            and you agree to share your username, email address, and affiliation with
                            CILogon, Custos, and Galaxy.
                        </small>
                    </p>
                </div>
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
        </div>
    </section>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import Multiselect from "vue-multiselect";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import svc from "./service";
import axios from "axios";
import { logoutClick } from "layout/menu";

Vue.use(BootstrapVue);

export default {
    components: {
        Multiselect,
    },
    data() {
        const galaxy = getGalaxyInstance();
        const oidc_idps = galaxy.config.oidc;
        return {
            items: [],
            showHelp: true,
            loading: false,
            doomedItem: null,
            errorMessage: null,
            enable_oidc: galaxy.config.enable_oidc,
            oidc_idps: oidc_idps,
            cilogon_idps: [],
            cilogonOrCustos: null,
            toggle_cilogon: false,
            selected: "",
            cilogonSelected: false,
        };
    },
    computed: {
        deleteButtonVariant() {
            return this.showDeleted ? "primary" : "secondary";
        },
        hasDoomed: {
            get() {
                return this.doomedItem !== null;
            },
            // This setter is here because vue-bootstrap modal
            // tries to set this property for unfathomable reasons
            set() {},
        },
        filtered_oidc_idps() {
            const filtered = Object.assign({}, this.oidc_idps);
            delete filtered.custos;
            delete filtered.cilogon;
            return filtered;
        },
    },
    watch: {
        showDeleted(deleted) {
            this.loadIdentities({ deleted });
        },
    },
    methods: {
        loadIdentities() {
            this.loading = true;
            svc.getIdentityProviders()
                .then((results) => {
                    this.items = results;
                    console.log("ITEMS: ", this.items);
                })
                .catch(this.setError("Unable to load connected external identities."))
                .finally(() => (this.loading = false));
        },
        onDisconnect(doomed) {
            this.doomedItem = doomed;
            if (doomed.id) {
                if (this.items.length > 1) {
                    // User must confirm that they want to disconnect the identity
                    this.$refs.deleteModal.show();
                } else {
                    // User is notified to reset password to use regular Galaxy login and avoid lockout
                    this.$refs.deleteAndResetModal.show();
                    this.setError(
                        "Before disconnecting this identity, you need to set your account password, " +
                            "in order to avoid being locked out of your account."
                    );
                }
            } else {
                this.setError(
                    "Before disconnecting this identity, you need to set your account password, " +
                        "in order to avoid being locked out of your account."
                );
            }
        },
        disconnectID() {
            // Called when the modal is closed with an "OK"
            svc.disconnectIdentity(this.doomedItem)
                .then(() => {
                    this.removeItem(this.doomedItem);
                })
                .catch((error) => {
                    if (error.data) {
                        this.setError("Unable to disconnect external identity.");
                    } else {
                        this.removeItem(this.doomedItem);
                    }
                })
                .finally(() => {
                    this.removeItem(this.doomedItem);
                    this.doomedItem = null;
                });
        },
        disconnectAndReset() {
            // Disconnects the user's final ext id and logouts of current session
            this.disconnectID();
            logoutClick();
        },
        removeItem(item) {
            this.items = this.items.filter((o) => o != item);
        },
        submitOIDCLogin(idp) {
            svc.saveIdentity(idp)
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
        getCILogonIdps: function () {
            const rootUrl = getAppRoot();
            axios.get(`${rootUrl}authnz/get_cilogon_idps`).then((response) => {
                this.cilogon_idps = response.data;
                //List is originally sorted by OrganizationName which can be different from DisplayName
                this.cilogon_idps.sort((a, b) => (a.DisplayName > b.DisplayName ? 1 : -1));
            });
        },
        submitCILogon(idp) {
            const rootUrl = getAppRoot();
            
            axios
                .post(`${rootUrl}authnz/${idp}/login/?idphint=${this.selected.EntityID}`)
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
        toggleCILogon(idp) {
            this.toggle_cilogon = !this.toggle_cilogon;
            this.cilogonOrCustos = this.toggle_cilogon ? idp : null;
        },
        setError(msg) {
            return (err) => {
                this.errorMessage = msg;
                console.warn(err);
            };
        },
    },
    created() {
        this.loadIdentities(), this.getCILogonIdps();
    },
};
</script>

<style lang="scss">
@import "~bootstrap/scss/functions";
@import "~bootstrap/scss/variables";
@import "~bootstrap/scss/mixins";
@import "~bootstrap/scss/utilities/spacing";
@import "scss/theme/blue.scss";
@import "scss/mixins";

.operations {
    margin-bottom: 0;

    ul {
        @include list_reset();
        display: flex;
        li:not(:first-child) {
            @extend .ml-2;
        }
    }
}

// General Layout

.external-id {
    // header sticks, bottom part scrolls
    @include scrollingListLayout("header", ".scroll-container");

    // title left, icons right
    .external-id-title {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;

        // top icon menu
        .operations {
            li {
                a,
                a::before {
                    font-size: 1rem;
                    color: $gray-400;
                }
                a.active::before,
                a:hover::before {
                    color: $brand-primary;
                }
            }
        }
    }
    .external-subheading {
        margin-top: 1rem;
    }
}

// Single list item

.external-id-key {
    header hgroup {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        user-select: none;

        > * {
            margin-bottom: 0;
        }
    }

    form {
        @extend .my-3;
        @extend .pt-3;
        // removes weird double arrows on select
        .custom-select {
            background: none;
        }
        // Allow side-by-side labels to work
        .form-row {
            display: flex;
            input,
            select {
                max-width: none;
            }
            label {
                font-weight: 400;
            }
        }

        // button list at bottom of form
        footer {
            display: flex;
            flex-direction: row;
            justify-content: flex-end;
            @extend .pt-3;

            button:not(:first-child) {
                @extend .ml-1;
            }
        }
    }

    // icon menu
    .operations {
        list-style-type: none;

        .delete a,
        button {
            @include fontawesome($fa-var-times);
        }
    }
}

// Transitions
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
    opacity: 0;
}

// Delete modal
#disconnectIDModal {
    .modal-body {
        display: none;
    }
    .modal-dialog {
        max-width: 300px;
    }
}
</style>
