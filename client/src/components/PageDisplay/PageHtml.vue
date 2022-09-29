<template>
    <div>
        <p v-html="page.content" />
    </div>
</template>

<script>
export default {
    props: {
        page: {
            type: Object,
            required: true,
        },
    },
};
</script>
