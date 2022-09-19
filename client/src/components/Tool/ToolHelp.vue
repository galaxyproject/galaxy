<template>
    <div class="form-help form-text mt-4" v-html="content" />
</template>

<script>
export default {
    props: {
        content: {
            type: String,
            required: true,
        },
    },
};
</script>
