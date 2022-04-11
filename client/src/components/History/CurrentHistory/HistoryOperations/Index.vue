<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button
                    title="Select Items"
                    class="show-history-content-selectors-btn rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!hasMatches"
                    :pressed="showSelection"
                    @click="toggleSelection">
                    <Icon icon="check-square" />
                </b-button>
                <b-button
                    title="Collapse Items"
                    class="rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!expandedCount"
                    @click="$emit('collapse-all')">
                    <Icon icon="compress" />
                </b-button>
            </b-button-group>
            <b-button-group v-if="showSelection">
                <slot name="selection-operations" />
            </b-button-group>
            <DefaultOperations
                v-else
                :history="history"
                :show-selection="showSelection"
                :has-matches="hasMatches"
                :expanded-count="expandedCount" />
        </nav>
    </section>
</template>

<script>
import DefaultOperations from "./Operations";

export default {
    components: {
        DefaultOperations,
    },
    props: {
        history: { type: Object, required: true },
        showSelection: { type: Boolean, required: true },
        hasMatches: { type: Boolean, required: true },
        expandedCount: { type: Number, required: false, default: 0 },
    },
    methods: {
        toggleSelection() {
            this.$emit("update:show-selection", !this.showSelection);
        },
    },
};
</script>

<style lang="scss">
// remove borders around buttons in menu
.content-operations .btn-group .btn {
    border-color: transparent !important;
    text-decoration: none;
    border-radius: 0px;
}
</style>
