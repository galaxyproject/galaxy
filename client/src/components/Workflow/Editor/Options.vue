<template>
    <div class="panel-header-buttons">
        <span v-if="canvas">
            <b-button
                id="workflow-home-button"
                role="button"
                title="Edit Attributes"
                variant="link"
                aria-label="Edit Attributes"
                v-b-tooltip.hover
                @click="$emit('onAttributes')"
            >
                <span class="fa fa-pencil-alt" />
            </b-button>
            <b-button
                id="workflow-save-button"
                role="button"
                title="Save Workflow"
                variant="link"
                aria-label="Save Workflow"
                v-b-tooltip.hover
                @click="$emit('onSave')"
            >
                <span class="fa fa-floppy-o" />
            </b-button>
            <b-button
                id="workflow-report-button"
                role="button"
                title="Edit Report"
                variant="link"
                aria-label="Edit Report"
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
                v-b-tooltip.hover
            >
                <template v-slot:button-content>
                    <span class="fa fa-cog" />
                </template>
                <b-dropdown-item href="#" @click="$emit('onSaveAs')"
                    ><span class="fa fa-floppy-o mr-1" />Save As...</b-dropdown-item
                >
                <b-dropdown-item href="#" @click="$emit('onLayout')"
                    ><span class="fa fa-align-left mr-1" />Auto Layout</b-dropdown-item
                >
                <b-dropdown-item href="#" @click="$emit('onDownload')"
                    ><span class="fa fa-download mr-1" />Download</b-dropdown-item
                >
            </b-dropdown>
            <b-button
                id="workflow-run-button"
                role="button"
                title="Run Workflow"
                variant="link"
                aria-label="Run Workflow"
                v-b-tooltip.hover
                @click="$emit('onRun')"
            >
                <span class="fa fa-play" />
            </b-button>
        </span>
        <span v-else>
            <b-button
                id="workflow-canvas-button"
                role="button"
                title="Return to Workflow"
                sm="size"
                variant="link"
                aria-label="Return to Workflow"
                @click="$emit('onEdit')"
            >
                <span class="fa fa-times" />
            </b-button>
        </span>
    </div>
</template>

<script>
export default {
    props: {
        canvas: {
            type: Boolean,
            required: true,
        },
    },
};
</script>
