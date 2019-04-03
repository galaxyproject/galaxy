<template>
    <section class="cloud-auth pt-1">
        <header>

            <hgroup class="cloud-auth-title">
                <h1>Manage Cloud Authorization</h1>
                <nav class="operations">
                    <ul>
                        <li class="help">
                            <a @click.prevent="showHelp = !showHelp"
                                v-b-tooltip.hover 
                                aria-label="Instructions"
                                title="Instructions">
                                <span>Instructions</span>
                            </a>
                        </li>
                        <li class="filter">
                            <a @click.prevent="showFilter = !showFilter"
                                v-b-tooltip.hover 
                                aria-label="Filter Results" 
                                title="Filter Results">
                                <span>Filter</span>
                            </a>
                        </li>
                        <li class="create">
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
                <button variant="success" @click="onCreate">
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
                        @expand="onExpand(credential, $event)" />
                </transition-group>

            </b-list-group>
        </div>

        <b-modal id="deleteCredentialModal" ref="deleteModal" 
            title="Delete Item?" size="sm"
            @ok="onConfirmDelete"
            @cancel="onCancelDelete">
        </b-modal>

    </section>
    
</template>

<script>

import CloudAuthItem from "./CloudAuthItem";
import { Credential } from "./model";
import svc from "./model/service";

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
            loading: false
        }
    },
    computed: {
        filteredItems() {
            return this.items
                .filter(o => o.filter(this.filter));
        },
        filterDescription() {
            return `${this.filteredItems.length} matches out of ${this.items.length} items`;
        },
        deleteButtonVariant() {
            return this.showDeleted ? "primary": "secondary";
        }
    },
    watch: {
        showDeleted(deleted) {
            this.loadCredentials({ deleted });
        }
    },
    methods: {
        onCreate() {
            this.addItem(Credential.create());
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
                .catch(err => console.warn('bad save', err))
                .finally(() => item.loading = false);
        },
        onDelete(doomed) {
            // bootstrapVue modal v-model property is bugged
            // so need to set and retrieve the doomed item manually
            this.doomedItem = doomed;
            this.$refs.deleteModal.show();
        },
        onConfirmDelete() {

            let doomed = this.doomedItem;
            doomed.loading = true;

            svc.deleteCredential(doomed)
                .then(() => this.removeItem(doomed))
                .catch(err => console.warn('bad delete', err))
                .finally(() => {
                    doomed.loading = false;
                    this.onCancelDelete();
                });
        },
        onCancelDelete() {
            this.doomedItem = null;
        },
        onExpand(credential, { expanded }) {
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
        loadCredentials(params = {}) {
            this.loading = true;
            svc.listCredentials(params)
                .then(items => this.items = items)
                .catch(err => console.warn("bad load", err))
                .finally(() => this.loading = false);
        }
    },
    created() {
        this.loadCredentials();
    }
}

</script>

<style lang="scss" src="./CloudAuth.scss"></style>