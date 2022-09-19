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
            <b-button-group v-show="showSelection">
                <slot name="selection-operations" />
            </b-button-group>
            <DefaultOperations
                v-show="!showSelection"
                :history="history"
                @update:operation-running="onUpdateOperationStatus" />
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
        expandedCount: { type: Number, default: 0 },
    },
    methods: {
        toggleSelection() {
            this.$emit("update:show-selection", !this.showSelection);
        },
        onUpdateOperationStatus(updateTime) {
            this.$emit("update:operation-running", updateTime);
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
