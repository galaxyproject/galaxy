<template>
    <div>test</div>
</template>

<script>
export default {
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
    created() {
        console.log(this.args);
    },
};
</script>
