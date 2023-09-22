<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { fetcher } from "@/schema";

const jobLock = ref(false);
const jobLockUpdating = ref(true);

const jobLockStatus = fetcher.path("/api/job_lock").method("get").create();
const jobLockUpdate = fetcher.path("/api/job_lock").method("put").create();

watch(jobLock, async (newVal) => {
    jobLockUpdating.value = true;
    const { data } = await jobLockUpdate({ active: jobLock.value });
    jobLock.value = data.active;
    jobLockUpdating.value = false;
});

onMounted(async () => {
    // TODO: see if we can upstream an optional arg when no params are required?
    // i.e. jobLockStatus() instead of jobLockStatus({})
    const response = await jobLockStatus({});
    jobLock.value = response.data.active;
    jobLockUpdating.value = false;
});
</script>
<template>
    <b-form-group>
        <b-form-checkbox id="prevent-job-dispatching" v-model="jobLock" :disabled="jobLockUpdating" switch size="lg">
            Job dispatching is currently
            <strong>{{ jobLock ? "locked" : "unlocked" }}</strong>
        </b-form-checkbox>
    </b-form-group>
</template>
