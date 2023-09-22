<script setup lang="ts">
import { computed } from "vue";
import { BDropdown, BDropdownItem, BButton } from "bootstrap-vue";
import { useConfirmDialog } from "@/composables/confirmDialog";

const emit = defineEmits<{
    (e: "onAttributes"): void;
    (e: "onSave"): void;
    (e: "onReport"): void;
    (e: "onSaveAs"): void;
    (e: "onLayout"): void;
    (e: "onLint"): void;
    (e: "onUpgrade"): void;
    (e: "onDownload"): void;
    (e: "onRun"): void;
}>();

const props = defineProps<{
    hasChanges?: boolean;
    hasInvalidConnections?: boolean;
    requiredReindex?: boolean;
}>();

const { confirm } = useConfirmDialog();

const saveHover = computed(() => {
    if (!props.hasChanges) {
        return "Workflow has no changes";
    } else if (props.hasInvalidConnections) {
        return "Workflow has invalid connections, review and remove invalid connections";
    } else {
        return "Save Workflow";
    }
});

async function onSave() {
    if (props.hasInvalidConnections) {
        console.log("getting confirmation");
        const confirmed = await confirm(
            `Workflow has invalid connections. You can save the workflow, but it may not run correctly.`,
            {
                id: "save-workflow-confirmation",
                okTitle: "Save Workflow",
            }
        );
        if (confirmed) {
            emit("onSave");
        }
    } else {
        emit("onSave");
    }
}
</script>
<template>
    <div class="panel-header-buttons">
        <b-button
            id="workflow-home-button"
            v-b-tooltip.hover
            role="button"
            title="Edit Attributes"
            variant="link"
            aria-label="Edit Attributes"
            class="editor-button-attributes"
            @click="$emit('onAttributes')">
            <span class="fa fa-pencil-alt" />
        </b-button>
        <b-button-group v-b-tooltip class="editor-button-save-group" :title="saveHover">
            <b-button
                id="workflow-save-button"
                role="button"
                variant="link"
                aria-label="Save Workflow"
                class="editor-button-save"
                :disabled="!hasChanges"
                @click="onSave">
                <span class="fa fa-floppy-o" />
            </b-button>
        </b-button-group>
        <b-button
            id="workflow-report-button"
            v-b-tooltip.hover
            role="button"
            title="Edit Report"
            variant="link"
            aria-label="Edit Report"
            class="editor-button-report"
            @click="$emit('onReport')">
            <span class="fa fa-edit" />
        </b-button>
        <b-dropdown
            id="workflow-options-button"
            v-b-tooltip.hover
            no-caret
            right
            role="button"
            title="Workflow Options"
            variant="link"
            aria-label="Workflow Options"
            class="editor-button-options">
            <template v-slot:button-content>
                <span class="fa fa-cog" />
            </template>
            <b-dropdown-item href="#" @click="$emit('onSaveAs')"
                ><span class="fa fa-floppy-o" />Save As...</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLayout')"
                ><span class="fa fa-align-left" />Auto Layout</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLint')"
                ><span class="fa fa-magic" />Best Practices</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onUpgrade')"
                ><span class="fa fa-recycle" />Upgrade Workflow</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onDownload')"
                ><span class="fa fa-download" />Download</b-dropdown-item
            >
        </b-dropdown>
        <b-button
            id="workflow-run-button"
            v-b-tooltip.hover
            role="button"
            title="Run Workflow"
            variant="link"
            aria-label="Run Workflow"
            class="editor-button-run"
            @click="$emit('onRun')">
            <span class="fa fa-play" />
        </b-button>
    </div>
</template>
