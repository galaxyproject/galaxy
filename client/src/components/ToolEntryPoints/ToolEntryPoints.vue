<template>
    <div class="infomessagelarge">
        <p v-if="entryPointsForJob(jobId).length == 0">
            Waiting for InteractiveTool result view(s) to become available.
        </p>
        <p v-else-if="entryPointsForJob(jobId).length == 1">
            <span v-if="entryPointsForJob(jobId)[0].active">
                There is an InteractiveTool result view available,
                <a v-b-tooltip title="Open Interactive Tool" :href="entryPointsForJob(jobId)[0].target" target="_blank">
                    Open
                    <FontAwesomeIcon icon="external-link-alt" />
                </a>
            </span>
            <span v-else>
                There is an InteractiveTool result view available, waiting for view to become active...
            </span>
        </p>
        <div v-else>
            There are multiple InteractiveTool result views available:
            <ul>
                <li v-for="entryPoint of entryPointsForJob(jobId)" :key="entryPoint.id">
                    {{ entryPoint.name }}
                    <span v-if="entryPoint.active">
                        <a v-b-tooltip title="Open Interactive Tool" :href="entryPoint.target" target="_blank">
                            (Open
                            <FontAwesomeIcon icon="external-link-alt" />)
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
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getAppRoot } from "onload/loadConfig";
import { mapState } from "pinia";
import { useEntryPointStore } from "stores/entryPointStore";

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
    computed: {
        ...mapState(useEntryPointStore, ["entryPointsForJob"]),
        interactiveToolsLink: function () {
            return getAppRoot() + "interactivetool_entry_points/list";
        },
    },
};
</script>
