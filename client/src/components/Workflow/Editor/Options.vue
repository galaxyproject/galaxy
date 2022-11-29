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
            <FontAwesomeIcon icon="fa-pencil-alt" />
        </b-button>
        <b-button-group v-b-tooltip class="editor-button-save-group" title="Save Workflow">
            <b-button
                id="workflow-save-button"
                role="button"
                variant="link"
                aria-label="Save Workflow"
                class="editor-button-save"
                :disabled="!hasChanges"
                @click="$emit('onSave')">
                <FontAwesomeIcon icon="far fa-save" />
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
            <FontAwesomeIcon icon="fa-edit" />
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
                <FontAwesomeIcon icon="fa-cog" />
            </template>
            <b-dropdown-item href="#" @click="$emit('onSaveAs')"
                ><FontAwesomeIcon icon="far fa-save" />Save As...</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLayout')"
                ><FontAwesomeIcon icon="fa-align-left" />Auto Layout</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLint')"
                ><FontAwesomeIcon icon="fa-magic" />Best Practices</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onUpgrade')"
                ><FontAwesomeIcon icon="fa-recycle" />Upgrade Workflow</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onDownload')"
                ><FontAwesomeIcon icon="fa-download" />Download</b-dropdown-item
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
            <FontAwesomeIcon icon="fa-play" />
        </b-button>
    </div>
</template>

<script>
import { BDropdown, BDropdownItem, BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faPencilAlt,
    faEdit,
    faCog,
    faAlignLeft,
    faMagic,
    faRecycle,
    faDownload,
} from "@fortawesome/free-solid-svg-icons";
import { faSave } from "@fortawesome/free-regular-svg-icons";

library.add(faPencilAlt, faEdit, faCog, faAlignLeft, faMagic, faRecycle, faDownload, faSave);

export default {
    components: {
        BDropdown,
        BDropdownItem,
        BButton,
        FontAwesomeIcon,
    },
    props: {
        hasChanges: {
            type: Boolean,
        },
        requiredReindex: {
            type: Boolean,
        },
    },
};
</script>
