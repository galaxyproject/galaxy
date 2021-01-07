<template>
    <b-button class="p-1" v-bind="$attrs" v-on="$listeners" :title="title" variant="link" size="sm" v-b-tooltip>
        <i v-if="icon" :class="icon" />
        <span class="sr-only">{{ title }}</span>
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
