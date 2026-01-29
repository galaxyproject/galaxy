<template>
    <div class="drop-zone d-flex align-items-center justify-content-center w-100 h-100 p-2 position-absolute rounded" />
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";
.drop-zone {
    pointer-events: none;
    z-index: 100;
    opacity: 0.2;
    background-color: $brand-info;
}
</style>
