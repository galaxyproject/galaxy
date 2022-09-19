<template>
    <b-form-group label="Administrative Job Lock" label-for="prevent-job-dispatching">
        <b-form-checkbox id="prevent-job-dispatching" v-model="jobLock" switch>
            Job dispatching is currently
            <strong>{{ jobLockDisplay ? "locked" : "unlocked" }}</strong>
        </b-form-checkbox>
    </b-form-group>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export default {
    data() {
        return {
            jobLock: false,
            jobLockDisplay: false,
        };
    },
    watch: {
        jobLock(newVal) {
            this.handleJobLock(axios.put(`${getAppRoot()}api/job_lock`, { active: this.jobLock }));
        },
    },
    created() {
        this.initJobLock();
    },
    methods: {
        initJobLock() {
            this.handleJobLock(axios.get(`${getAppRoot()}api/job_lock`));
        },
        handleJobLock(axiosPromise) {
            axiosPromise
                .then((response) => {
                    this.jobLock = response.data.active;
                    this.jobLockDisplay = response.data.active;
                })
                .catch((error) => {
                    console.error(error);
                });
        },
    },
};
</script>
