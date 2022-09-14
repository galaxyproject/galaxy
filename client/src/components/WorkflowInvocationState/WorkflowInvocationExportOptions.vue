<template>
    <b-card-group deck>
        <b-card title="BioCompute Object Export" class="export-plugin-card">
            <bio-compute-object-export-card :invocation-id="invocationId" />
        </b-card>
        <!-- Add more export plugins here -->
    </b-card-group>
</template>

<script>
import BioComputeObjectExportCard from "./Export/BioComputeObjectExportCard.vue";
export default {
    components: { BioComputeObjectExportCard },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
};
</script>
