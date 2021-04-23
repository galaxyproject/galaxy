<template>
    <b-dropdown text="Select history..." size="sm" boundary="viewport" class="select-history">
        <b-dropdown-item
            v-for="h in histories"
            :key="h.id"
            :active="currentHistory.id == h.id"
            @click="$emit('update:currentHistory', h)"
        >
            {{ h.name }}
        </b-dropdown-item>
    </b-dropdown>
</template>

<script>
export default {
    props: {
        currentHistory: { type: Object, required: true },
        histories: { type: Array, default: () => [] },
    },
};
</script>
<style>
.select-history .dropdown-menu {
    max-width: 90%;
    overflow-x: auto;
}
</style>
