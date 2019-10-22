<template>
    <section class="external-id">
        <header>
            <b-alert dismissible fade variant="warning" :show="errorMessage !== null" @dismissed="errorMessage = null">
                {{ errorMessage }}
            </b-alert>

            <hgroup class="external-id-title">
                <h1>Manage External Identities</h1>
            </hgroup>
        </header>

        <b-list-group class="external-id-key">
            <ul class="operations">
                <li  class="delete" v-for="item in filteredItems" v-bind:key="item">
                    <button
                        :key="item.id"
                        :credential="credential"
                        @click="onDisconnect(item)"
                        aria-label="Disconnect External Identity"
                        title="Disconnect External Identity"
                    >
                        <span>Disconnect External Identity</span>
                    </button>
                    {{ item.provider }}
                </li>
            </ul>
        </b-list-group>

        <b-modal
            v-model="hasDoomed"
            centered
            id="disconnectIDModal"
            ref="deleteModal"
            title="Disconnect Identity?"
            size="sm"
            @ok="disconnectID"
            @cancel="doomedItem = null"
        >
        </b-modal>
    </section>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ExternalIdKey from "./ExternalIdKey";
import { Credential } from "./model";
import svc from "./model/service";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalIdKey
    },
    data() {
        return {
            items: [],
            showHelp: true,
            loading: false,
            doomedItem: null,
            errorMessage: null
        };
    },
    computed: {
        filteredItems() {
            return this.items;
        },
        deleteButtonVariant() {
            return this.showDeleted ? "primary" : "secondary";
        },
        hasDoomed: {
            get() {
                return this.doomedItem !== null;
            },
            // This setter is here because vue-bootstrap modal
            // tries to set this property for unfathomable reasons
            set() {}
        }
    },
    watch: {
        showDeleted(deleted) {
            this.loadIdentities({ deleted });
        }
    },
    methods: {
        loadIdentities() {
            this.loading = true;
            console.log("before loading");
            console.log(this.items);
            svc.getIdentityProviders()
                .then(results => {
                    this.items = results;
                })
                .catch(this.setError("Unable to load connected external identities."))
                .finally(() => (this.loading = false));
            console.log("after loading");
            console.log(this.items);
        },
        onDisconnect(doomed) {
            console.log(this.doomedItem);
            this.doomedItem = doomed;
            console.log(this.doomedItem);
            if (doomed.id) {
                // User must confirm that they want to disconnect the identity
                this.$refs.deleteModal.show();
            } else {
                this.removeItem(doomed);
                this.doomedItem = null;
            }
        },
        disconnectID() {
            // Called when the modal is closed with an "OK"
            svc.disconnectIdentity() //here!!!!
                .then(() => this.removeItem(this.doomedItem))
                .catch(this.setError("Unable to disconnect external identity."))
                .finally(() => {
                    this.doomedItem = null;
                });
            console.log("after disconnectID");
            console.log(this.items);
        },
        removeItem(item) {
            this.items = this.items.filter(o => o !== item);
        },
        setError(msg) {
            return err => {
                this.errorMessage = msg;
                console.warn(err);
            };
        }
    },
    created() {
        this.loadIdentities();
    }
};
</script>

<style lang="scss">
@import "~bootstrap/scss/functions";
@import "~bootstrap/scss/variables";
@import "~bootstrap/scss/mixins";
@import "~bootstrap/scss/utilities/spacing";

@import "scss/theme/blue.scss";
@import "scss/mixins";

// TODO: build reusable icon menu? Maybe make into a component?
// The existing one has lots of reusability problems

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

            .cloudKeyHelp a {
                @include fontawesome($fa-var-info-circle);
            }
        }
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

        // removes wierd double arrows on select
        .custom-select {
            background: none;
        }

        // Undo butchering from base.css so side-by-side labels work
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

        .delete a, button {
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
