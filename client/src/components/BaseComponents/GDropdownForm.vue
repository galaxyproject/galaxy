<script setup lang="ts"></script>

<template>
    <form class="px-4 py-3" role="presentation" @click.stop @submit.prevent>
        <slot />
    </form>
</template>
