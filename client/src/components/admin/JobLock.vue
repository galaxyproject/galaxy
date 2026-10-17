<script setup lang="ts">
import { BFormGroup } from "bootstrap-vue";
import { onMounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

const jobLock = ref(false);
const jobLockUpdating = ref(true);

watch(jobLock, async (_newVal) => {
    jobLockUpdating.value = true;
    const { data, error } = await GalaxyApi().PUT("/api/job_lock", { body: { active: jobLock.value } });
    if (error) {
        rethrowSimple(error);
    }
    jobLock.value = data.active;
    jobLockUpdating.value = false;
});

onMounted(async () => {
    const { data, error } = await GalaxyApi().GET("/api/job_lock");
    if (error) {
        rethrowSimple(error);
    }
    jobLock.value = data.active;
    jobLockUpdating.value = false;
});
</script>
<template>
    <BFormGroup>
        <GCheckbox id="prevent-job-dispatching" v-model="jobLock" :disabled="jobLockUpdating" switch size="large">
            Job dispatching is currently
            <strong>{{ jobLock ? "locked" : "unlocked" }}</strong>
        </GCheckbox>
    </BFormGroup>
</template>
