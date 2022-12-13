<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import axios, { type AxiosError, type AxiosPromise, type AxiosResponse } from "axios";
import { getAppRoot } from "@/onload/loadConfig";

const jobLock = ref(false);
const jobLockDisplay = ref(false);

watch(jobLock, (newVal) => {
    handleJobLock(axios.put(`${getAppRoot()}api/job_lock`, { active: jobLock.value }));
});

onMounted(() => {
    handleJobLock(axios.get(`${getAppRoot()}api/job_lock`));
});

function handleJobLock(axiosPromise: AxiosPromise) {
    axiosPromise
        .then((response: AxiosResponse) => {
            jobLock.value = response.data.active;
            jobLockDisplay.value = response.data.active;
        })
        .catch((error: AxiosError) => {
            console.error(error);
        });
}
</script>
<template>
    <b-form-group>
        <b-form-checkbox id="prevent-job-dispatching" v-model="jobLock" switch size="lg">
            Job dispatching is currently
            <strong>{{ jobLockDisplay ? "locked" : "unlocked" }}</strong>
        </b-form-checkbox>
    </b-form-group>
</template>
