<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

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
    <b-form-group>
        <b-form-checkbox id="prevent-job-dispatching" v-model="jobLock" :disabled="jobLockUpdating" switch size="lg">
            作业调度当前是
            <strong>{{ jobLock ? "锁定" : "解锁" }}</strong>
        </b-form-checkbox>
    </b-form-group>
</template>
