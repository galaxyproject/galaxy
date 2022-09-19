<template>
    <div class="infomessagelarge">
        <p v-if="entryPoints.length == 0">Waiting for InteractiveTool result view(s) to become available.</p>
        <p v-else-if="entryPoints.length == 1">
            <span v-if="entryPoints[0].active">
                There is an InteractiveTool result view available,
                <a :href="entryPoints[0].target">click here to display</a>.
            </span>
            <span v-else>
                There is an InteractiveTool result view available, waiting for view to become active...
            </span>
        </p>
        <div v-else>
            There are multiple InteractiveTool result views available:
            <ul>
                <li v-for="entryPoint of entryPoints" :key="entryPoint.id">
                    {{ entryPoint.name }}
                    <span v-if="entryPoint.active"> (<a :href="entryPoint.target">click here to display</a>) </span>
                    <span v-else> (waiting to become active...) </span>
                </li>
            </ul>
        </div>

        You may also access all active InteractiveTools from the
        <a :href="interactiveToolsLink">User menu</a>.
    </div>
</template>

<script>
import { clearPolling, pollUntilActive } from "mvc/entrypoints/poll";
import { getAppRoot } from "onload/loadConfig";

export default {
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            entryPoints: [],
        };
    },
    computed: {
        interactiveToolsLink: function () {
            return getAppRoot() + "interactivetool_entry_points/list";
        },
    },
    created: function () {
        this.pollEntryPoints();
    },
    beforeDestroy: function () {
        clearPolling();
    },
    methods: {
        pollEntryPoints: function () {
            const onUpdate = (entryPoints) => {
                this.entryPoints = entryPoints;
            };
            const onError = (e) => {
                console.error(e);
            };
            pollUntilActive(onUpdate, onError, { job_id: this.jobId });
        },
    },
};
</script>
