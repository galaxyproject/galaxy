<template>
    <b-button
        v-if="offset > 200"
        v-b-tooltip.noninteractive.hover
        class="ui-btn-back-to-top btn-circle"
        title="Scroll To Top"
        variant="info"
        @click="$emit('click')">
        <i class="fa fa-arrow-up" />
    </b-button>
</template>

<script>
export default {
    props: {
        offset: {
            type: Number,
            default: 0,
        },
    },
};
</script>
