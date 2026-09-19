<template>
    <div>
        {{ info }}
    </div>
</template>

<script>
export default {
    props: {
        value: {
            required: true,
        },
        info: {
            type: String,
            default: null,
        },
    },
};
</script>
