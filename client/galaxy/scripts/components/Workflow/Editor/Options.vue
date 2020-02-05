<template>
    <div class="panel-header-buttons">
        <span v-if="canvas">
            <a
                id="workflow-run-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Run"
                aria-label="Run"
                @click="$emit('onRun')"
            >
                <span class="fa fa-play"/>
            </a>
            <a
                id="workflow-save-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Save"
                aria-label="Save"
                @click="$emit('onSave')"
            >
                <span class="fa fa-floppy-o"/>
            </a>
            <a
                id="workflow-report-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Edit Report"
                aria-label="Edit Report"
                @click="$emit('onReport')"
            >
                <span class="fa fa-edit"/>
            </a>

            <a
                id="workflow-options-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Workflow options"
                aria-label="Workflow options"
                ref="save-button"
            >
                <span class="fa fa-cog"/>
            </a>
            <b-dropdown
                no-caret right
                class="panel-header-button"
            >
                <template v-slot:button-content>
                    <span class="fa fa-cog"/>
                </template>
                <b-dropdown-item href="#" @click="$emit('onSaveAs')">Save As</b-dropdown-item>
                <b-dropdown-item href="#" @click="$emit('onAttributes')">Edit Attributes</b-dropdown-item>
                <b-dropdown-item href="#" @click="$emit('onLayout')">Auto Layout</b-dropdown-item>
                <b-dropdown-item href="#" @click="$emit('onDownload')">Download</b-dropdown-item>
            </b-dropdown>
        </span>
        <span v-else>
            <a
                id="workflow-report-help-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Report Syntax Help"
                aria-label="Report Syntax Help"
                @click="$emit('onReportHelp')"
            >
                <span class="fa fa-question"/>
            </a>
            <a
                id="workflow-canvas-button"
                class="panel-header-button"
                href="javascript:void(0)"
                role="button"
                title="Edit Workflow"
                aria-label="Edit Workflow"
                @click="$emit('onEdit')"
            >
                <span class="fa fa-sitemap fa-rotate-270"/>
            </a>
        </span>
    </div>
</template>

<script>

export default {
    props: {
        canvas: {
            type: Boolean,
            required: true
        }
    }
};
</script>