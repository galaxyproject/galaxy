<script setup lang="ts">
import { format, parseISO } from "date-fns";
import { computed } from "vue";
import Multiselect from "vue-multiselect";

// TODO: Use schema type once `/api/workflows/{workflow_id}/versions` is typed.
interface WorkflowVersion {
    steps: number;
    update_time: string;
    version: number;
}

const props = defineProps<{
    version: number;
    versions: WorkflowVersion[];
}>();

const emit = defineEmits<{
    (e: "onVersion", version: number): void;
}>();

const activeVersion = computed<{ label: string; version: number }>({
    get() {
        return versionOptions.value.find((v) => v.version === props.version) || { label: "", version: -1 };
    },
    set(value: { label: string; version: number }) {
        emit("onVersion", value.version);
    },
});

const versionOptions = computed(() => {
    const versions = [];
    for (let i = 0; i < props.versions.length; i++) {
        const currentVersion = props.versions[i];
        if (currentVersion) {
            let update_time;
            if (currentVersion.update_time) {
                update_time = `${format(parseISO(currentVersion.update_time), "MMM do yyyy")}`;
            } else {
                update_time = "";
            }
            const label = `${currentVersion.version + 1}: ${update_time}, ${currentVersion.steps} steps`;
            versions.push({
                version: i,
                label: label,
            });
        }
    }
    return versions;
});

const selectedVersionLabel = computed(() => {
    const selected = versionOptions.value.find((v) => v.version === props.version);
    return selected ? selected.label : "";
});
</script>

<template>
    <Multiselect
        v-model="activeVersion"
        data-description="workflow version select"
        track-by="version"
        :options="versionOptions"
        label="label"
        select-label=""
        deselect-label=""
        :placeholder="selectedVersionLabel" />
</template>
