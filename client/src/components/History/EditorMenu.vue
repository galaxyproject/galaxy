<template>
    <nav class="edit-controls">
        <IconButton
            :title="label('Edit') | l"
            class="edit-button mb-1"
            :pressed="editing"
            icon="pen"
            @click="$emit('update:editing', !editing)"
            data-description="editor toggle" />

        <template v-if="editing">
            <!-- save -->
            <IconButton
                :title="label('Save') | l"
                class="save-button mb-1"
                :class="{ disabled: !valid }"
                icon="save"
                @click="$emit('save')"
                data-description="editor save button" />

            <!-- revert -->
            <IconButton
                :title="label('Revert') | l"
                class="revert-changes-button mb-1"
                :class="{ disabled: !dirty }"
                icon="undo"
                @click="$emit('revert')"
                data-description="editor revert button" />

            <!-- form status -->
            <IconButton
                :title="statusLabel | l"
                class="status-button mb-1"
                :class="{ valid: valid, disabled: !valid }"
                :icon="valid ? 'check' : 'exclamation-triangle'"
                variant="link"
                data-description="editor status" />
        </template>
    </nav>
</template>

<script>
import IconButton from "components/IconButton";

export default {
    components: {
        IconButton,
    },
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
