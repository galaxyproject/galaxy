<script setup>
import { Services } from "../services";
import { computed, ref, watch } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
    queryTrsServer: {
        type: String,
        default: null,
    },
    trsSelection: {
        type: Object,
        default: null,
    },
});

const emit = defineEmits(["onError", "onTrsSelection"]);

const loading = ref(true);
const selection = ref(null);
const trsServers = ref([]);
const trsSelection = ref(null);

const showDropdown = computed(() => {
    return trsServers.value.length > 1;
});

watch(props, () => {
    selection.value = props.trsSelection;
});

const services = new Services();

const _configureTrsServers = () => {
    services.getTrsServers().then((servers) => {
        trsServers.value = servers;
        const queryTrsServer = props.queryTrsServer;
        if (queryTrsServer) {
            for (const server of servers) {
                if (server.id == queryTrsServer) {
                    trsSelection.value = server;
                    break;
                }
                if (possibleServeUrlsMatch(server.api_url, queryTrsServer)) {
                    trsSelection.value = server;
                    break;
                }
                if (possibleServeUrlsMatch(server.link_url, queryTrsServer)) {
                    trsSelection.value = server;
                    break;
                }
            }
        }
        if (trsSelection.value === null) {
            if (queryTrsServer) {
                emit("onError", "Failed to find requested TRS server " + queryTrsServer);
            }
            trsSelection.value = servers[0];
        }
        selection.value = trsSelection.value;
        loading.value = false;
        onTrsSelection(trsSelection.value);
    });
};

const onTrsSelection = (selection) => {
    selection.value = selection;
    emit("onTrsSelection", selection);
};

const possibleServeUrlsMatch = (a, b) => {
    // let http://trs_server.org/ match with https://trs_server.org for instance,
    // we'll only use the one configured on the backend for making actual calls, but
    // allow some robustness in matching it
    a = a.replace(/^https?:\/\//, "").replace(/\/$/, "");
    b = b.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return a == b;
};

_configureTrsServers();
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown);
</script>

<template>
    <span v-if="!loading" class="m-1 text-muted">
        <span v-if="showDropdown" class="dropdown">
            <b-link
                id="dropdownTrsServer"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                class="font-weight-bold">
                {{ selection.label }}
                <FontAwesomeIcon icon="fa-caret-down" />
            </b-link>
            <div class="dropdown-menu" aria-labelledby="dropdownTrsServer">
                <a
                    v-for="serverSelection in trsServers"
                    :key="serverSelection.id"
                    class="dropdown-item"
                    href="javascript:void(0)"
                    role="button"
                    @click.prevent="onTrsSelection(serverSelection)"
                    >{{ serverSelection.label }}</a
                >
            </div>
        </span>
        <span v-else>
            <b-link :href="selection.link_url" target="_blank" class="font-weight-bold" :title="selection.doc">
                {{ selection.label }}
            </b-link>
        </span>
    </span>
</template>

<style scoped>
span.dropdown {
    display: inline-block;
}
</style>
