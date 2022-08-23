<script setup>
const props = defineProps({
    title: String,
});
</script>

<template>
    <div class="mt-2 mb-4">
        <div class="title-bar my-2">
            <h2>{{ props.title }}</h2>
            <div class="stripe"></div>
        </div>
        <slot />
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.title-bar {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 1em;

    h2 {
        font-size: 1.25em;
        margin: 0;
        font-weight: 700;
    }

    .stripe {
        display: block;
        height: 1px;
        background-color: $brand-secondary;
    }
}
</style>
