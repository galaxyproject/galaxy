<template>
    <div class="donemessagelarge">
        <div v-if="usedToolRequest">
            You used the fancy new API... something new will be here.
            <img
                src="https://www.animatedimages.org/data/media/695/animated-under-construction-image-0055.gif"
                alt="90s style under construction" />
        </div>
        <div v-else>
            <p>
                Started tool <b>{{ toolName }}</b> and successfully added {{ nJobsText }} to the queue.
            </p>
            <p>The tool uses {{ nInputsText }}:</p>
            <ul>
                <li v-for="item of inputs" :key="item.hid">
                    <b>{{ item.hid }}: {{ item.name }}</b>
                </li>
            </ul>
            <p>It produces {{ nOutputsText }}:</p>
            <ul>
                <li v-for="item of jobResponse.outputs" :key="item.hid">
                    <b>{{ item.hid }}: {{ item.name }}</b>
                </li>
            </ul>
        </div>
        <p>
            You can check the status of queued jobs and view the resulting data by refreshing the History panel. When
            the job has been run the status will change from 'running' to 'finished' if completed successfully or
            'error' if problems were encountered.
        </p>
    </div>
</template>

<script>
export default {
    props: {
        jobResponse: {
            type: Object,
            required: true,
        },
        toolName: {
            type: String,
            required: true,
        },
        usedToolRequest: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        nOutputs() {
            return this.jobResponse && this.jobResponse.outputs ? this.jobResponse.outputs.length : 0;
        },
        nJobs() {
            return this.jobResponse && this.jobResponse.jobs ? this.jobResponse.jobs.length : 0;
        },
        nJobsText() {
            return this.nJobs > 1 ? `${this.nJobs} jobs` : `1 job`;
        },
        nOutputsText() {
            return this.nOutputs > 1 ? `${this.nOutputs} outputs` : `this output`;
        },
    },
};
</script>
