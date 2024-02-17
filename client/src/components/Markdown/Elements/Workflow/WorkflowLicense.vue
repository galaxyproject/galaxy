<script setup lang="ts">
import License from "@/components/License/License.vue";

interface WorkflowLicenseProps {
    licenseId?: string;
}

const props = withDefaults(defineProps<WorkflowLicenseProps>(), {
    licenseId: null,
});
</script>

<template>
    <span>
        <p v-if="!props.licenseId">
            <i>Workflow does not define a license.</i>
        </p>
        <License v-else :license-id="props.licenseId" />
    </span>
</template>
