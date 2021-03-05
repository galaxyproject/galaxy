<template>
    <div :disabled="disabled" v-b-tooltip.hover.d50 :title="title"><slot /></div>
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
