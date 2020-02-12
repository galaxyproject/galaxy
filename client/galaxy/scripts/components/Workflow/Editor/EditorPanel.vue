<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <slot name="buttons" />
            </div>
        </div>
        <div class="unified-panel-body workflow-right">
            <slot name="attributes" />
            <div id="right-content" class="right-content" />
        </div>
    </div>
</template>

<script>
export default {
    name: "EditorPanel"
};
</script>
