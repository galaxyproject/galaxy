<template>
    <b-list-group-item class="cloud-auth-key"
        :class="statusClasses"
        :variant="variant"
        :button="!expanded">

        <header>
            <hgroup>
                <h4 @click.prevent="expand()">{{ credential.title }}</h4>
                <nav class="operations">
                    <ul>
                        <transition name="fade">
                            <li class="save" v-if="expanded && credential.dirty">
                                <a @click.prevent="$emit('save', credential)"
                                    v-b-tooltip.hover 
                                    aria-label="Save Key"
                                    title="Save Key">
                                    <span>Save</span>
                                </a>
                            </li>
                        </transition>
                        <li class="delete">
                            <a @click.prevent="$emit('delete', credential)"
                                v-b-tooltip.hover 
                                aria-label="Delete this key" 
                                title="Delete this key">
                                <span>Delete</span>
                            </a>
                        </li>
                        <li class="details">
                            <a @click.prevent="expand()"
                                v-b-tooltip.hover 
                                aria-label="Show Details"
                                title="Show Details">
                                <span>Details</span>
                            </a>
                        </li>
                    </ul>
                </nav>
            </hgroup>
        </header>

        <credential-form v-if="expanded"
            class="mt-4 pt-4 border-top"
            v-model="credential" 
            @click.self="expand()"
            @save="$emit('save', credential)"
            @delete="$emit('delete', credential)" />

    </b-list-group-item>
</template>

<script>

import Vue from "vue";
import { Credential } from "./model";
import CredentialForm from "./CredentialForm";

export default {
    components: {
        CredentialForm
    },
    props: {
        credential: { type: Credential, required: true }
    },
    computed: {
        statusClasses() {
            let { expanded, valid, dirty, loading } = this.credential;
            return { loading, expanded, valid, dirty, collapsed: !expanded };
        },
        variant() {
            return this.expanded ? "" : "primary";
        },
        expanded() {
            return this.credential.expanded;
        }
    },
    methods: {
        expand(forceState) {
            let expanded = (forceState !== undefined) ? forceState : !this.expanded;
            this.$emit("expand", { expanded });
        }
    }
}

</script>

<style lang="scss" src="./CloudAuthItem.scss"></style>
