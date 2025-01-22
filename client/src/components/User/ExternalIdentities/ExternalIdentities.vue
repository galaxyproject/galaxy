<template>
    <section class="external-id">
        <b-alert :show="!!connectExternal" variant="info">
            You are logged in. You can now connect the Galaxy user account with the email <i>{{ userEmail }}</i
            >, to your preferred external provider.
        </b-alert>
        <b-alert :show="!!existingEmail" variant="warning">
            Note: We found a Galaxy account matching the email of this identity, <i>{{ existingEmail }}</i
            >. The active account <i>{{ userEmail }}</i> has been linked to this external identity. If you wish to link
            this identity to a different account, you will need to disconnect it from this account first.
        </b-alert>
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
                <h1 class="h-lg">Manage External Identities</h1>
            </hgroup>

            <p>
                Users with existing Galaxy user accounts (e.g., via Galaxy username and password) can associate their
                account with their 3rd party identities. For instance, if a user associates their Galaxy account with
                their Google account, then they can log in to Galaxy either using their Galaxy username and password, or
                their Google account. Whichever method they use they will be assuming same Galaxy user account, hence
                having access to the same histories, workflows, datasets, libraries, etc.
            </p>

            <p>
                See more information, including a list of supported identity providers,
                <a href="https://galaxyproject.org/authnz/use/oidc/">here</a>.
            </p>
        </header>

        <div v-if="items.length" class="external-subheading">
            <h2 class="h-md">Connected External Identities</h2>
            <b-button
                v-for="item in items"
                :key="item.email"
                aria-label="Disconnect External Identity"
                title="Disconnect External Identity"
                class="d-block mt-3"
                @click="onDisconnect(item)">
                Disconnect {{ item.provider_label.charAt(0).toUpperCase() + item.provider_label.slice(1) }} -
                {{ item.email }}
            </b-button>

            <b-modal
                id="disconnectIDModal"
                ref="deleteModal"
                centered
                title="Disconnect Identity?"
                size="sm"
                @ok="disconnectID"
                @cancel="doomedItem = null"></b-modal>

            <b-modal
                id="disconnectAndResetModal"
                ref="deleteAndResetModal"
                centered
                title="Deleting last external identity"
                @ok="disconnectAndReset"
                @cancel="doomedItem = null">
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

        <div v-if="enable_oidc" class="external-subheading">
            <h2 class="h-md">Connect Other External Identities</h2>
            <ExternalLogin />
        </div>
    </section>
</template>

<script>
import { getGalaxyInstance } from "app";
import BootstrapVue from "bootstrap-vue";
import { Toast } from "composables/toast";
import { sanitize } from "dompurify";
import { userLogout } from "utils/logout";
import Vue from "vue";

import svc from "./service";

import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            items: [],
            showHelp: true,
            loading: false,
            doomedItem: null,
            errorMessage: null,
            enable_oidc: galaxy.config.enable_oidc,
            cilogonOrCustos: null,
            userEmail: galaxy.user.get("email"),
        };
    },
    computed: {
        connectExternal() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.has("connect_external") && urlParams.get("connect_external") == "true";
        },
        deleteButtonVariant() {
            return this.showDeleted ? "primary" : "secondary";
        },
        existingEmail() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.get("email_exists");
        },
        hasDoomed: {
            get() {
                return this.doomedItem !== null;
            },
            // This setter is here because vue-bootstrap modal
            // tries to set this property for unfathomable reasons
            set() {},
        },
    },
    watch: {
        showDeleted(deleted) {
            this.loadIdentities({ deleted });
        },
    },
    created() {
        this.loadIdentities();
    },
    mounted() {
        const params = new URLSearchParams(window.location.search);
        const notificationMessage = sanitize(params.get("notification"));
        Toast.success(notificationMessage);
    },
    methods: {
        loadIdentities() {
            this.loading = true;
            svc.getIdentityProviders()
                .then((results) => {
                    this.items = results;
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
            userLogout();
        },
        removeItem(item) {
            this.items = this.items.filter((o) => o != item);
        },
        setError(msg) {
            return (err) => {
                this.errorMessage = msg;
                console.warn(err);
            };
        },
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
