<script setup lang="ts"></script>

<template>
    <div class="vr-container mx-3">
        <div class="vr" />
        <span class="vr-text">
            <slot />
        </span>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.vr-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1px;
}

.vr {
    width: 1px;
    height: 100%;
    background-color: $brand-secondary;
}

.vr-text {
    position: absolute;
    background-color: $body-bg;
}
</style>
