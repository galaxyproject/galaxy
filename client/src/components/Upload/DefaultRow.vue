<template>
    <div ref="target" />
</template>

<script>
import UploadRow from "mvc/upload/default/default-row";

export default {
    props: {
        listGenomes: {
            type: Array,
            required: true,
        },
        listExtensions: {
            type: Array,
            required: true,
        },
        extensions: {
            type: Array,
            required: true,
        },
        extension: {
            type: String,
            required: true,
        },
        genome: {
            type: String,
            required: true,
        },
        model: {
            type: Object,
            required: true,
        },
    },
    mounted() {
        new UploadRow(
            {
                extension: this.extension,
                extensions: this.extensions,
                genome: this.genome,
                listExtensions: this.listExtensions,
                listGenomes: this.listGenomes,
            },
            { model: this.model }
        ).$el.appendTo(this.$refs.target);
    },
};
</script>
