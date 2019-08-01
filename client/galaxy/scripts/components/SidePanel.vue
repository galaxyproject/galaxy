<template>
    <div :id="side" class="unified-panel-outer-wrap">

        <component :is="currentPanel" v-bind="currentPanelProperties"></component>

        <div class="unified-panel-footer">
            <div class="panel-collapse" :class="side"></div>
            <div class="drag"></div>
        </div>
    </div>
</template>

<script>
    export default {
        name: "SidePanel",
        props: ['currentPanel', 'currentPanelProperties', 'side'],
    }
</script>

<style scoped>
</style>