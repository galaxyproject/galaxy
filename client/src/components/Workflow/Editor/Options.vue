<template>
    <div class="panel-header-buttons">
        <b-button
            id="workflow-home-button"
            role="button"
            title="Edit Attributes"
            variant="link"
            aria-label="Edit Attributes"
            class="editor-button-attributes"
            v-b-tooltip.hover
            @click="$emit('onAttributes')"
        >
            <span class="fa fa-pencil-alt" />
        </b-button>
        <b-button-group class="editor-button-save-group" v-b-tooltip title="Save Workflow">
            <b-button
                id="workflow-save-button"
                role="button"
                variant="link"
                aria-label="Save Workflow"
                class="editor-button-save"
                :disabled="!hasChanges"
                @click="$emit('onSave')"
            >
                <span class="fa fa-floppy-o" />
            </b-button>
        </b-button-group>
        <b-button
            id="workflow-report-button"
            role="button"
            title="Edit Report"
            variant="link"
            aria-label="Edit Report"
            class="editor-button-report"
            v-b-tooltip.hover
            @click="$emit('onReport')"
        >
            <span class="fa fa-edit" />
        </b-button>
        <b-dropdown
            no-caret
            right
            id="workflow-options-button"
            role="button"
            title="Workflow Options"
            variant="link"
            aria-label="Workflow Options"
            class="editor-button-options"
            v-b-tooltip.hover
        >
            <template v-slot:button-content>
                <span class="fa fa-cog" />
            </template>
            <b-dropdown-item href="#" @click="$emit('onSaveAs')"
                ><icon class="fa-floppy-o" />Save As...</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLayout')"
                ><icon class="fa-align-left" />Auto Layout</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onLint')"><icon class="fa-magic" />Best Practices</b-dropdown-item>
            <b-dropdown-item href="#" @click="$emit('onUpgrade')"
                ><icon class="fa-recycle" />Upgrade Workflow</b-dropdown-item
            >
            <b-dropdown-item href="#" @click="$emit('onDownload')"
                ><icon class="fa-download" />Download</b-dropdown-item
            >
        </b-dropdown>
        <b-button
            id="workflow-run-button"
            role="button"
            title="Run Workflow"
            variant="link"
            aria-label="Run Workflow"
            class="editor-button-run"
            v-b-tooltip.hover
            @click="$emit('onRun')"
        >
            <span class="fa fa-play" />
        </b-button>
    </div>
</template>

<script>
import { BDropdown, BDropdownItem, BButton } from "bootstrap-vue";

export default {
    components: {
        BDropdown,
        BDropdownItem,
        BButton,
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
