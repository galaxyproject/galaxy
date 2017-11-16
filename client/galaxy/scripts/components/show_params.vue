<template>
    <div id="show-dataset-params" class="dataset-metadata">
        <p v-html="datasetId">
        </p>
    </div>
</template>

<script>

export default {
    props: {
        metadataId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
           historyId: ""
        };
    },
    computed: {
        datasetId: function() {
            return this.metadataId
        }
    }
}
</script>
