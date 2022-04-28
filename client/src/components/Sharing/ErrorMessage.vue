<template>
    <span>
        <span v-for="(part, index) in parts" :key="index">
            {{ part }}
            <a v-if="index < parts.length - 1" :href="link" class="require-login-link"> logged in </a>
        </span>
    </span>
</template>

<script>
export default {
    props: {
        message: {
            type: String,
            required: true,
        },
        root: {
            type: String,
            required: true,
        },
    },
    computed: {
        link() {
            return `${this.root}login?redirect=${encodeURIComponent(window.location)}`;
        },
        parts() {
            return this.message.split("logged in");
        },
    },
};
</script>
