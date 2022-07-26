<template>
    <b-list-group-item class="cloud-auth-key" :class="statusClasses" :variant="variant" :button="!expanded">
        <header>
            <hgroup>
                <h4 @click.prevent="expand()">{{ credential.title }}</h4>
                <nav class="operations">
                    <ul>
                        <transition name="fade">
                            <li v-if="expanded && credential.dirty" class="save">
                                <a
                                    v-b-tooltip.hover
                                    aria-label="Save Key"
                                    title="Save Key"
                                    @click.prevent="$emit('save', credential)">
                                    <span>Save Key</span>
                                </a>
                            </li>
                        </transition>
                        <li class="delete">
                            <a
                                v-b-tooltip.hover
                                aria-label="Delete Key"
                                title="Delete Key"
                                @click.prevent="$emit('delete', credential)">
                                <span>Delete Key</span>
                            </a>
                        </li>
                        <li class="details">
                            <a
                                v-b-tooltip.hover
                                aria-label="Show Details"
                                title="Show Details"
                                @click.prevent="expand()">
                                <span>Details</span>
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

export default {
    components: {
        CredentialForm,
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
