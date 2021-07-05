<template>
    <b-button class="p-1" v-bind="$attrs" v-on="$listeners" :title="title | localize" variant="link" size="sm">
        <i v-if="icon" :class="icon" />
        <span class="sr-only">{{ title | localize }}</span>
    </b-button>
</template>

<script>
export default {
    props: {
        icon: { type: String, required: false, default: "" },
        title: { type: String, required: true },
    },
};
</script>
