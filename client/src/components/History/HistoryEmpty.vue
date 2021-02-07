<template>
    <b-alert show>
        <h4>
            <i class="fa fa-info-circle"></i>
            <span v-localize>This history is empty.</span>
        </h4>
        <p>
            <a href="#" @click.prevent="openUploader" v-localize>You can load your own data</a> or
            <a href="#" @click.prevent="clickDataLink" v-localize>get data from an external source</a>.
        </p>
    </b-alert>
</template>

<script>
export default {
    methods: {
        openUploader() {
            this.eventHub.$emit("upload:open");
        },
        clickDataLink() {
            this.eventHub.$emit("openToolSection", "getext");
        },
    },
};
</script>
