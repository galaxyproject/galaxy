<template>
    <div>
        <span v-if="isError" class="fa fa-exclamation-triangle text-danger" />
        <span v-if="isPaused" class="fa fa-pause text-info" />
        <b-link :href="item.url" class="ml-1"><b>{{ item.name }}</b></b-link>
    </div>
</template>
<script>

export default {
    props: {
        item: Object
    },
    data() {
        return {};
    },
    computed: {
        isError() {
            return this.item.state === "error";
        },
        isPaused() {
            return this.item.state === "paused";
        }
    }
};
</script>
