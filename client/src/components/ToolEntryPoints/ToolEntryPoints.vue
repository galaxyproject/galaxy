<template>
    <div class="infomessagelarge">
        <p v-if="getEntryPointsForJob(jobId).length == 0">
            Waiting for InteractiveTool result view(s) to become available.
        </p>
        <p v-else-if="getEntryPointsForJob(jobId).length == 1">
            <span v-if="getEntryPointsForJob(jobId)[0].active">
                There is an InteractiveTool result view available,
                <a
                    v-b-tooltip
                    title="Open Interactive Tool"
                    :href="getEntryPointsForJob(jobId)[0].target"
                    target="_blank">
                    Open
                    <font-awesome-icon icon="external-link-alt" />
                </a>
            </span>
            <span v-else>
                There is an InteractiveTool result view available, waiting for view to become active...
            </span>
        </p>
        <div v-else>
            There are multiple InteractiveTool result views available:
            <ul>
                <li v-for="entryPoint of getEntryPointsForJob(jobId)" :key="entryPoint.id">
                    {{ entryPoint.name }}
                    <span v-if="entryPoint.active">
                        <a v-b-tooltip title="Open Interactive Tool" :href="entryPoint.target" target="_blank">
                            (Open
                            <font-awesome-icon icon="external-link-alt" />)
                        </a>
                    </span>
                    <span v-else> (waiting to become active...) </span>
                </li>
            </ul>
        </div>

        You may also access all active InteractiveTools from the
        <a :href="interactiveToolsLink">User menu</a>.
    </div>
</template>

<script>
import { useEntryPointStore } from "@/stores/entryPointStore";
import { getAppRoot } from "onload/loadConfig";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faExternalLinkAlt);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    setup() {
        const { getEntryPointsForJob, ensurePollingEntryPoints } = useEntryPointStore();
        return { getEntryPointsForJob, ensurePollingEntryPoints };
    },
    computed: {
        interactiveToolsLink: function () {
            return getAppRoot() + "interactivetool_entry_points/list";
        },
    },
    created: function () {
        this.ensurePollingEntryPoints();
    },
};
</script>
