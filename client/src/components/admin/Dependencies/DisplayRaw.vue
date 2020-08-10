<template>
    <span class="fa fa-code" :title="asJson" />
</template>

<script>
export default {
    props: {
        object: {
            type: Object,
            required: true,
        },
    },
    computed: {
        asJson: function () {
            return JSON.stringify(this.object);
        },
    },
};
</script>
