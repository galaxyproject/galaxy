<template>
    <span>
        <span class="loading-message">{{ message }}.<span class="blinking">..</span></span>
    </span>
</template>
<script>
export default {
    props: {
        message: {
            type: String,
            default: "No Jobs Exist In This History",
        },
    },
};
</script>
