<template>
    <b-card-group deck>
        <b-card title="BioCompute Object Export" class="export-plugin-card">
            <bio-compute-object-export-card :invocation-id="invocationId" />
        </b-card>
        <b-card title="To File" class="export-plugin-card">
            <p>
                <a class="model-export-link" :href="exportHref"><b>Export Invocation to File</b></a>
            </p>
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
    computed: {
        exportHref: function () {
            return `${getAppRoot()}workflows/invocations/${this.invocationId}/export`;
        },
    },
};
</script>
