<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSave } from "@fortawesome/free-regular-svg-icons";
import {
    faAlignLeft,
    faCog,
    faDownload,
    faEdit,
    faHistory,
    faPencilAlt,
    faPlay,
    faRecycle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BDropdown, BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";

library.add(faPencilAlt, faEdit, faCog, faAlignLeft, faDownload, faPlay, faHistory, faSave, faRecycle);

const emit = defineEmits<{
    (e: "onAttributes"): void;
    (e: "onSave"): void;
    (e: "onCreate"): void;
    (e: "onReport"): void;
    (e: "onSaveAs"): void;
    (e: "onLayout"): void;
    (e: "onUpgrade"): void;
    (e: "onDownload"): void;
    (e: "onRun"): void;
}>();

const props = defineProps<{
    isNewTempWorkflow?: boolean;
    hasChanges?: boolean;
    hasInvalidConnections?: boolean;
    requiredReindex?: boolean;
    currentActivePanel: string;
}>();

const { confirm } = useConfirmDialog();

const saveHover = computed(() => {
    if (props.isNewTempWorkflow) {
        return "Save Workflow";
    } else if (!props.hasChanges) {
        return "Workflow has no changes";
    } else if (props.hasInvalidConnections) {
        return "Workflow has invalid connections, review and remove invalid connections";
    } else {
        return "Save Workflow";
    }
});

function emitSaveOrCreate() {
    if (props.isNewTempWorkflow) {
        emit("onCreate");
    } else {
        emit("onSave");
    }
}

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
            emitSaveOrCreate();
        }
    } else {
        emitSaveOrCreate();
    }
}
</script>

<template>
    <div class="panel-header-buttons">
        <BButton
            id="workflow-home-button"
            v-b-tooltip.hover.noninteractive
            role="button"
            title="Edit Attributes"
            variant="link"
            aria-label="Edit Attributes"
            class="editor-button-attributes"
            @click="emit('onAttributes')">
            <FontAwesomeIcon icon="fa fa-pencil-alt" />
        </BButton>

        <b-button-group v-b-tooltip.hover.noninteractive class="editor-button-save-group" :title="saveHover">
            <BButton
                id="workflow-save-button"
                role="button"
                :variant="isNewTempWorkflow ? 'primary' : 'link'"
                aria-label="Save Workflow"
                class="editor-button-save"
                :disabled="!isNewTempWorkflow && !hasChanges"
                @click="onSave">
                <FontAwesomeIcon icon="far fa-save" />
            </BButton>
        </b-button-group>

        <BButton
            id="workflow-report-button"
            v-b-tooltip.hover.noninteractive
            role="button"
            title="Edit Report"
            variant="link"
            aria-label="Edit Report"
            class="editor-button-report"
            :disabled="isNewTempWorkflow"
            @click="emit('onReport')">
            <FontAwesomeIcon icon="fa fa-edit" />
        </BButton>

        <BDropdown
            id="workflow-options-button"
            v-b-tooltip.hover.noninteractive
            no-caret
            right
            role="button"
            title="Workflow Options"
            variant="link"
            aria-label="Workflow Options"
            class="editor-button-options"
            :disabled="isNewTempWorkflow">
            <template v-slot:button-content>
                <FontAwesomeIcon icon="fa fa-cog" />
            </template>

            <BDropdownItem href="#" @click="emit('onSaveAs')">
                <FontAwesomeIcon icon="far fa-save" /> Save As...
            </BDropdownItem>

            <BDropdownItem href="#" @click="emit('onLayout')">
                <FontAwesomeIcon icon="fa fa-align-left" /> Auto Layout
            </BDropdownItem>

            <BDropdownItem href="#" @click="emit('onUpgrade')">
                <FontAwesomeIcon icon="fa fa-recycle" /> Upgrade Workflow
            </BDropdownItem>

            <BDropdownItem href="#" @click="emit('onDownload')">
                <FontAwesomeIcon icon="fa fa-download" /> Download
            </BDropdownItem>
        </BDropdown>

        <BButton
            id="workflow-run-button"
            v-b-tooltip.hover.noninteractive
            role="button"
            title="Run Workflow"
            variant="link"
            aria-label="Run Workflow"
            class="editor-button-run"
            :disabled="isNewTempWorkflow"
            @click="emit('onRun')">
            <FontAwesomeIcon icon="fa fa-play" />
        </BButton>
    </div>
</template>
