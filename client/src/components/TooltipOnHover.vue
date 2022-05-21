<template>
    <div v-b-tooltip.hover :disabled="disabled" :title="title"><slot /></div>
</template>
<script>
export default {
    props: {
        title: {
            type: String,
            required: true,
        },
        disabled: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
};
</script>
