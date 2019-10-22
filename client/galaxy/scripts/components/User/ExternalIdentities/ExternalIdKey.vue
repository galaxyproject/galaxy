<template>
    <b-list-group-item class="external-id-key" :class="statusClasses" :button="!expanded">
        <header>
            <hgroup>
                <h4 @click.prevent="expand()">{{ credential.title }}</h4>
                <nav class="operations">
                    <ul>
                        <li class="delete">
                            <a
                                @click.prevent="$emit('delete', credential)"
                                v-b-tooltip.hover
                                aria-label="Disconnect External Identity"
                                title="Disconnect External Identity"
                            >
                                <span>Disconnect External Identityyyyyyyyyy</span>
                            </a>
                        </li>
                    </ul>
                </nav>
            </hgroup>
        </header>
    </b-list-group-item>
</template>

<script>

export default {
    props: {
        credential: { type: Credential, required: true }
    },
    computed: {
        statusClasses() {
            const { expanded, valid, dirty, loading } = this.credential;
            return { loading, expanded, valid, dirty, collapsed: !expanded };
        },
        expanded() {
            return this.credential.expanded;
        }
    },
    methods: {
        expand(forceState) {
            const expanded = forceState !== undefined ? forceState : !this.expanded;
            this.$emit("expand", { expanded });
        }
    }
};
</script>
