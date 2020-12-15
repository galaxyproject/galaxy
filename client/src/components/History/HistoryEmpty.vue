<template>
    <b-alert show>
        <h4>
            <i class="fa fa-info-circle"></i>
            This history is empty.
        </h4>
        <p>
            You can <a href="#" @click.prevent="openUploader" v-localize>load your own data</a> or
            <a href="#" @click.prevent="clickDataLink" v-localize>get data from an external source</a>.
        </p>
    </b-alert>
</template>

<script>
export default {
    methods: {
        openUploader() {
            this.eventHub.$emit("openToolSection", "getext");
            this.$nextTick(() => {
                this.eventHub.$emit("clickTool", "upload1");
            });
        },
        clickDataLink() {
            this.eventHub.$emit("openToolSection", "getext");
        },
    },
};
</script>
