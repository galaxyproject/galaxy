<template>
    <section class="cloud-auth">
        <header>
            <b-alert dismissible fade variant="warning" :show="errorMessage !== null" @dismissed="errorMessage = null">
                {{ errorMessage }}
            </b-alert>

            <hgroup class="cloud-auth-title">
                <h1 v-localize class="h-lg">Manage Cloud Authorization</h1>
                <nav class="operations">
                    <ul>
                        <li class="cloudKeyHelp">
                            <a
                                v-b-tooltip.hover
                                :class="{ active: showHelp }"
                                aria-label="Instructions"
                                title="Instructions"
                                @click.prevent="showHelp = !showHelp">
                                <span>Instructions</span>
                            </a>
                        </li>
                        <li class="cloudKeyFilter">
                            <a
                                v-b-tooltip.hover
                                :class="{ active: showFilter }"
                                aria-label="Filter Results"
                                title="Filter Results"
                                @click.prevent="showFilter = !showFilter">
                                <span>Filter</span>
                            </a>
                        </li>
                        <li class="createCloudKey">
                            <a
                                v-b-tooltip.hover
                                aria-label="Create New Key"
                                title="Create New Key"
                                @click.prevent="onCreate">
                                <span>Create New Key</span>
                            </a>
                        </li>
                    </ul>
                </nav>
            </hgroup>

            <transition name="fade">
                <hgroup v-if="showHelp">
                    <p>See the online <a href="https://galaxyproject.org/authnz/">Documentation</a>.</p>
                </hgroup>
            </transition>

            <transition name="fade">
                <hgroup v-if="showFilter">
                    <b-form-group :description="filterDescription">
                        <b-form-input v-model="filter" type="text" placeholder="Filter" />
                    </b-form-group>
                </hgroup>
            </transition>

            <b-button-group class="mb-4">
                <button name="createNewKey" @click="onCreate">Create New Authorization Key</button>
            </b-button-group>
        </header>

        <div class="scroll-container">
            <b-list-group>
                <transition-group name="fade">
                    <cloud-auth-item
                        v-for="credential in filteredItems"
                        :key="credential.counter"
                        :credential="credential"
                        class="mb-1"
                        @delete="onDelete"
                        @save="onSave"
                        @expand="expand(credential, $event)" />
                </transition-group>
            </b-list-group>
        </div>

        <b-modal
            id="deleteCredentialModal"
            ref="deleteModal"
            v-model="hasDoomed"
            centered
            title="Delete Key?"
            size="sm"
            @ok="deleteKey"
            @cancel="doomedItem = null">
        </b-modal>
    </section>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import CloudAuthItem from "./CloudAuthItem";
import { Credential } from "./model";
import svc from "./model/service";

Vue.use(BootstrapVue);

export default {
    components: {
        CloudAuthItem,
    },
    data() {
        return {
            items: [],
            filter: "",
            showHelp: true,
            showFilter: false,
            loading: false,
            doomedItem: null,
            errorMessage: null,
        };
    },
    computed: {
        filteredItems() {
            return this.items.filter((o) => o.match(this.filter));
        },
        filterDescription() {
            return `${this.filteredItems.length} matches out of ${this.items.length} items`;
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
            set() {},
        },
    },
    watch: {
        showDeleted(deleted) {
            this.loadCredentials({ deleted });
        },
    },
    created() {
        this.loadCredentials();
    },
    methods: {
        loadCredentials(params = {}) {
            this.loading = true;
            svc.listCredentials(params)
                .then((items) => (this.items = items))
                .catch(this.setError("Unable to load cloud keys."))
                .finally(() => (this.loading = false));
        },
        onCreate() {
            const newItem = Credential.create({ expanded: true });
            this.addItem(newItem);
        },
        onSave(item) {
            if (!item.valid) {
                return;
            }
            item.loading = true;
            svc.saveCredential(item)
                .then((result) => {
                    item.id = result.id;
                    item.updateState();
                })
                .catch(this.setError("Unable to save key."))
                .finally(() => (item.loading = false));
        },
        onDelete(doomed) {
            this.doomedItem = doomed;
            if (doomed.id) {
                this.$refs.deleteModal.show();
            } else {
                this.removeItem(doomed);
                this.doomedItem = null;
            }
        },
        deleteKey() {
            // Called when the modal is closed with an "OK"
            svc.deleteCredential(this.doomedItem)
                .then(() => this.removeItem(this.doomedItem))
                .catch(this.setError("Unable to delete cloud key."))
                .finally(() => {
                    this.doomedItem = null;
                });
        },
        expand(credential, { expanded }) {
            credential.expanded = expanded;
            if (expanded) {
                this.items.filter((i) => i !== credential).forEach((i) => (i.expanded = false));
            }
        },
        addItem(item) {
            this.items = [...this.items, item];
        },
        removeItem(item) {
            this.items = this.items.filter((o) => o !== item);
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

.cloud-auth {
    // header sticks, bottom part scrolls
    @include scrollingListLayout("header", ".scroll-container");

    // title left, icons right
    .cloud-auth-title {
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
            .cloudKeyFilter a {
                @include fontawesome($fa-var-filter);
            }
            .createCloudKey a {
                @include fontawesome($fa-var-plus);
            }
        }
    }
}

// Single list item

.cloud-auth-key {
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
        .save a {
            @include fontawesome($fa-var-save);
        }
        .delete a {
            @include fontawesome($fa-var-times);
        }
        .details a {
            @include fontawesome($fa-var-window-minimize);
            &:hover {
                @include fontawesome($fa-var-window-maximize);
            }
        }
    }

    // reverse icons when key is expanded

    &.expanded .details a {
        @include fontawesome($fa-var-window-maximize);
        &:hover {
            @include fontawesome($fa-var-window-minimize);
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

#deleteCredentialModal {
    .modal-body {
        display: none;
    }
    .modal-dialog {
        max-width: 300px;
    }
}
</style>
