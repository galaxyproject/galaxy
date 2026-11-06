<template>
    <div id="app" class="widget-view">
        <router-view />
    </div>
</template>

<style lang="scss">
@import "../../style/scss/custom_theme_variables.scss";

// Views size themselves to their parent, as in the analysis app's center panel.
.widget-view {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    overflow: auto;
}
</style>
