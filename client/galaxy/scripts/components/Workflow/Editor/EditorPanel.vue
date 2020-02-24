<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <slot name="buttons" />
            </div>
        </div>
        <div class="unified-panel-body workflow-right">
            <div v-if="canvas" class="m-1">
                <slot name="attributes" />
                <div id="right-content" class="right-content" />
            </div>
            <ReportHelp v-else />
        </div>
    </div>
</template>

<script>
import ReportHelp from "./ReportHelp";

export default {
    name: "EditorPanel",
    components: {
        ReportHelp
    },
    props: {
        canvas: {
            type: Boolean,
            required: true
        }
    }
};
</script>
