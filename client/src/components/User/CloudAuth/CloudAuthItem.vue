<template>
    <b-list-group-item class="cloud-auth-key" :class="statusClasses" :variant="variant" :button="!expanded">
        <header>
            <hgroup>
                <h2 class="h-sm" @click.prevent="expand()">{{ credential.title }}</h2>
                <nav class="operations">
                    <ul>
                        <transition name="fade">
                            <li v-if="expanded && credential.dirty" class="save">
                                <a
                                    v-b-tooltip.hover
                                    aria-label="Save Key"
                                    title="Save Key"
                                    @click.prevent="$emit('save', credential)">
                                    <FontAwesomeIcon icon="fa-save" />
                                    <span class="sr-only">Save Key</span>
                                </a>
                            </li>
                        </transition>
                        <li class="delete">
                            <a
                                v-b-tooltip.hover
                                aria-label="Delete Key"
                                title="Delete Key"
                                @click.prevent="$emit('delete', credential)">
                                <FontAwesomeIcon icon="fa-times" />
                                <span class="sr-only">Delete Key</span>
                            </a>
                        </li>
                        <li class="details">
                            <a
                                v-b-tooltip.hover
                                aria-label="Show Details"
                                title="Show Details"
                                @click.prevent="expand()">
                                <FontAwesomeIcon icon="fa-window-minimize" class="minimize" />
                                <FontAwesomeIcon icon="fa-window-maximize" class="maximize" />
                                <span class="sr-only">Details</span>
                            </a>
                        </li>
                    </ul>
                </nav>
            </hgroup>
        </header>
        <!-- TODO: Restructure credential handling so we're not mutating the prop -->
        <!-- eslint-disable vue/no-mutating-props-->
        <credential-form
            v-if="expanded"
            v-model="credential"
            class="border-top"
            @click.self="expand()"
            @save="$emit('save', credential)"
            @delete="$emit('delete', credential)" />
        <!-- eslint-enable vue/no-mutating-props-->
    </b-list-group-item>
</template>

<script>
import { Credential } from "./model";
import CredentialForm from "./CredentialForm";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSave, faTimes, faWindowMinimize, faWindowMaximize } from "@fortawesome/free-solid-svg-icons";

library.add(faSave, faTimes, faWindowMinimize, faWindowMaximize);

export default {
    components: {
        CredentialForm,
        FontAwesomeIcon,
    },
    props: {
        credential: { type: Credential, required: true },
    },
    computed: {
        statusClasses() {
            const { expanded, valid, dirty, loading } = this.credential;
            return { loading, expanded, valid, dirty, collapsed: !expanded };
        },
        variant() {
            if (this.expanded) {
                return "";
            }
            if (this.credential.dirty) {
                return "warning";
            }
            if (!this.credential.valid) {
                return "danger";
            }
            return "primary";
        },
        expanded() {
            return this.credential.expanded;
        },
    },
    methods: {
        expand(forceState) {
            const expanded = forceState !== undefined ? forceState : !this.expanded;
            this.$emit("expand", { expanded });
        },
    },
};
</script>

<style lang="scss" scoped>
.cloud-auth-key {
    &:deep(.minimize) {
        display: inline-block;

        &:hover {
            display: none;
        }
    }

    &:deep(.maximize) {
        display: none;

        &:hover {
            display: inline-block;
        }
    }

    // reverse icons when key is expanded

    &.expanded {
        &:deep(.minimize) {
            display: none;

            &:hover {
                display: inline-block;
            }
        }

        &:deep(.maximize) {
            display: inline-block;

            &:hover {
                display: none;
            }
        }
    }
}
</style>
