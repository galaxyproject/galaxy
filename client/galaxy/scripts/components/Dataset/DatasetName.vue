<template>
    <div>
        <span v-if="isError" class="fa fa-exclamation-triangle text-danger mr-1" />
        <span v-if="isPaused" class="fa fa-pause text-info mr-1" />
        <b-link :href="item.url"><b>{{ item.name }}</b></b-link>
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
