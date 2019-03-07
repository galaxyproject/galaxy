<template>
    <div v-if="message" :class="[status + 'message']">{{ message }}</div>
</template>

<script>
export default {
    name: "Message",
    props: {
        message: {
            type: String,
            required: true
        },
        status: {
            type: String,
            default: "done"
        }
    }
};
</script>
