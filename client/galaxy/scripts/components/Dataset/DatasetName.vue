<template>
    <div>
        <span v-if="isError" class="fa fa-times-circle text-danger mr-1" />
        <span v-if="isPaused" class="fa fa-pause text-info mr-1" />
        <b-link href="#" @click.stop="showDataset">
            <b>{{ item.name }}</b>
        </b-link>
    </div>
</template>
<script>
export default {
    props: {
        item: Object
    },
    computed: {
        isError() {
            return this.item.state === "error";
        },
        isPaused() {
            return this.item.state === "paused";
        }
    },
    methods: {
        showDataset(item) {
            this.$emit("showDataset", this.item);
        }
    }
};
</script>
