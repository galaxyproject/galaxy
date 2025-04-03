<template>
    <div
        role="button"
        tabindex="0"
        @click="$emit('click')"
        @keydown.enter="$emit('click')"
        @keydown.space.prevent="$emit('click')">
        <slot />
    </div>
</template>
