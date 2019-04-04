<template>
    <section class="cloud-auth">
        <header>

            <b-alert dismissible fade variant="warning"
                :show="errorMessage !== null"
                @dismissed="errorMessage = null">
                {{ errorMessage }}
            </b-alert>

            <hgroup class="cloud-auth-title">
                <h1>Manage Cloud Authorization</h1>
                <nav class="operations">
                    <ul>
                        <li class="cloudKeyHelp">
                            <a :class="{ active: showHelp }"
                                @click.prevent="showHelp = !showHelp"
                                v-b-tooltip.hover 
                                aria-label="Instructions"
                                title="Instructions">
                                <span>Instructions</span>
                            </a>
                        </li>
                        <li class="cloudKeyFilter">
                            <a :class="{ active: showFilter }"
                                @click.prevent="showFilter = !showFilter"
                                v-b-tooltip.hover 
                                aria-label="Filter Results" 
                                title="Filter Results">
                                <span>Filter</span>
                            </a>
                        </li>
                        <li class="createCloudKey">
                            <a @click.prevent="onCreate"
                                v-b-tooltip.hover 
                                aria-label="Create New Key"
                                title="Create New Key">
                                <span>Create New Key</span>
                            </a>
                        </li>
                    </ul>
                </nav>
            </hgroup>

            <transition name="fade">
                <hgroup v-if="showHelp">
                    <p>See the online <a href="https://galaxyproject.org/cloud/authnz/">Documentation</a>.</p>
                </hgroup>
            </transition>

            <transition name="fade">
                <hgroup v-if="showFilter">
                    <b-form-group :description="filterDescription">
                        <b-form-input type="text" placeholder="Filter" 
                            v-model="filter" />
                    </b-form-group>
                </hgroup>
            </transition>

            <b-button-group class="mb-4">
                <button name="createNewKey" @click="onCreate">
                    Create New Authorization Key
                </button>
            </b-button-group>

        </header>

        <div class="scroll-container">
            <b-list-group>
                <transition-group name="fade">
                    <cloud-auth-item v-for="credential in filteredItems" 
                        :key="credential.counter"
                        :credential="credential"
                        class="mb-1"
                        @delete="onDelete"
                        @save="onSave"
                        @expand="expand(credential, $event)" />
                </transition-group>
            </b-list-group>
        </div>

        <b-modal v-model="hasDoomed" centered
            id="deleteCredentialModal" ref="deleteModal" 
            title="Delete Key?" size="sm"
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
        CloudAuthItem
    },
    data() {
        return {
            items: [],
            filter: "",
            showHelp: true,
            showFilter: false,
            loading: false,
            doomedItem: null,
            errorMessage: null
        }
    },
    computed: {
        filteredItems() {
            return this.items.filter(o => o.match(this.filter));
        },
        filterDescription() {
            return `${this.filteredItems.length} matches out of ${this.items.length} items`;
        },
        deleteButtonVariant() {
            return this.showDeleted ? "primary": "secondary";
        },
        hasDoomed: {
            get() { return this.doomedItem !== null; },
            // This setter is here because vue-bootstrap modal
            // tries to set this property for unfathomable reasons
            set() {}
        }
    },
    watch: {
        showDeleted(deleted) {
            this.loadCredentials({ deleted });
        }
    },
    methods: {
        loadCredentials(params = {}) {
            this.loading = true;
            svc.listCredentials(params)
                .then(items => this.items = items)
                .catch(this.setError("Unable to load cloud keys."))
                .finally(() => this.loading = false);
        },
        onCreate() {
            let newItem = Credential.create({ expanded: true });
            this.addItem(newItem);
        },
        onSave(item) {
            if (!item.valid) {
                return;
            }
            item.loading = true;
            svc.saveCredential(item)
                .then(result => {
                    item.id = result.id;
                    item.updateState();
                })
                .catch(this.setError("Unable to save key."))
                .finally(() => item.loading = false);
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
                this.items.filter(i => i !== credential)
                    .forEach(i => i.expanded = false);
            }
        },
        addItem(item) {
            this.items = [ ...this.items, item ];
        },
        removeItem(item) {
            this.items = this.items.filter(o => o !== item);
        },
        setError(msg) {
            return (err) => {
                this.errorMessage = msg;
                console.warn(err);
            }
        }
    },
    created() {
        this.loadCredentials();
    }
}

</script>

<style lang="scss" src="./CloudAuth.scss"></style>
