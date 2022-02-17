<template>
    <nav class="edit-controls">
        <b-button
            :title="label('Edit') | l"
            class="edit-button mb-1"
            :pressed="editing"
            @click="$emit('update:editing', !editing)"
            data-description="editor toggle">
            <Icon icon="pen" />
        </b-button>
        <template v-if="editing">
            <!-- save -->
            <b-button
                :title="label('Save') | l"
                class="save-button mb-1"
                :class="{ disabled: !valid }"
                @click="$emit('save')"
                data-description="editor save button">
                <Icon icon="save" />
            </b-button>

            <!-- revert -->
            <b-button
                :title="label('Revert') | l"
                class="revert-changes-button mb-1"
                :class="{ disabled: !dirty }"
                icon="undo"
                @click="$emit('revert')"
                data-description="editor revert button">
                <Icon icon="undo" />
            </b-button>

            <!-- form status -->
            <b-button
                :title="statusLabel | l"
                class="status-button mb-1"
                :class="{ valid: valid, disabled: !valid }"
                variant="link"
                data-description="editor status">
                <Icon :icon="valid ? 'check' : 'exclamation-triangle'" />
            </b-button>
        </template>
    </nav>
</template>

<script>
export default {
    props: {
        modelName: { type: String, required: true },
        editing: { type: Boolean, required: true },
        dirty: { type: Boolean, required: false, default: false },
        valid: { type: Boolean, required: false, default: false },
    },
    computed: {
        statusLabel() {
            const status = this.valid ? "Valid" : "Invalid";
            return `${status} ${this.modelName}`;
        },
    },
    methods: {
        label(verb) {
            return `${verb} ${this.modelName}`;
        },
    },
};
</script>

<style lang="scss">
.edit-controls .disabled {
    opacity: 0.25;
}
</style>
