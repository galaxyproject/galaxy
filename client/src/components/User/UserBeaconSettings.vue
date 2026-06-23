<script setup lang="ts">
import { faExchangeAlt, faPlus, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { BeaconHistory } from "@/api/histories";
import { createNewHistory, getBeaconHistories as fetchBeaconHistories } from "@/api/histories";
import { fetchBeaconSettings, toggleBeaconIntegration } from "@/api/users";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "../BaseComponents/GButton.vue";
import GModal from "../BaseComponents/GModal.vue";
import GTable from "../Common/GTable.vue";
import Heading from "../Common/Heading.vue";
import ExternalLink from "../ExternalLink.vue";
import UtcDate from "../UtcDate.vue";

const BEACON_HISTORY_NAME = "Beacon Export 📡";

const fields = [
    { key: "name", label: "Name", sortable: true },
    { key: "create_time", label: "Created", sortable: true },
    { key: "set_current", label: "" },
];

const Toast = useToast();

const historyStore = useHistoryStore();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const userId = computed(() => (currentUser.value && "id" in currentUser.value ? currentUser.value.id : undefined));

const enabled = ref(false);
const beaconHistories = ref<BeaconHistory[]>([]);
const loadingHistories = ref(false);
const historyOperationRunning = ref(false);
const togglingBeacon = ref(false);

async function getBeaconHistories() {
    loadingHistories.value = true;
    try {
        beaconHistories.value = await fetchBeaconHistories(BEACON_HISTORY_NAME);
    } catch (error) {
        Toast.error(errorMessageAsString(error, "Error fetching beacon histories"));
    } finally {
        loadingHistories.value = false;
    }
}

async function createBeaconHistory() {
    if (historyOperationRunning.value) {
        return;
    }

    const annotation = "Variants will be collected from VCF datasets in this history if beacon sharing is activated";

    historyOperationRunning.value = true;
    try {
        const response = await createNewHistory(BEACON_HISTORY_NAME);
        await historyStore.updateHistory(response.id, { name: BEACON_HISTORY_NAME, annotation });
        await getBeaconHistories();
    } catch (error) {
        Toast.error(errorMessageAsString(error, "Error creating beacon history"));
    } finally {
        historyOperationRunning.value = false;
    }
}

async function toggleBeacon(enable: boolean) {
    if (!userId.value) {
        Toast.error("User not found");
        return;
    }

    togglingBeacon.value = true;
    try {
        const response = await toggleBeaconIntegration(userId.value, enable);

        if (response.enabled !== enable) {
            Toast.error(`Failed to ${enable ? "enable" : "disable"} beacon sharing`);
            return;
        }
        enabled.value = enable;
    } catch (error) {
        Toast.error(errorMessageAsString(error, `Error ${enable ? "opting in to" : "opting out of"} beacon`));
    } finally {
        togglingBeacon.value = false;
    }
}

async function loadSettings() {
    if (!userId.value) {
        Toast.error("User not found");
        return;
    }

    try {
        const response = await fetchBeaconSettings(userId.value);
        enabled.value = response.enabled;
    } catch (error) {
        Toast.error(errorMessageAsString(error, "Error loading beacon settings"));
    }
}

async function onOpenModal() {
    await Promise.all([loadSettings(), getBeaconHistories()]);
}

async function switchHistory(historyId: string) {
    if (historyOperationRunning.value) {
        return;
    }

    historyOperationRunning.value = true;
    try {
        await historyStore.setCurrentHistory(historyId);
    } catch (error) {
        Toast.error(errorMessageAsString(error, "Error switching to beacon history"));
    } finally {
        historyOperationRunning.value = false;
    }
}

onOpenModal();
</script>

<template>
    <GModal
        id="modal-beacon"
        ref="modal"
        size="medium"
        :fixed-height="enabled"
        show
        title="Manage Beacon"
        @close="$emit('reset')">
        <!-- Explanation text-->
        <p>
            The
            <ExternalLink href="https://beacon-project.io">
                Global Alliance for Genomics & Health Beacon Project
            </ExternalLink>
            enables safe sharing of human genetic variants.
        </p>
        <p>
            Galaxy lets you use the Beacon protocol to share genetic variants directly from your analysis with the
            scientific community in the following anonymous way:
        </p>
        <p>
            For participating users, we will merge variant lists to be shared into a single Beacon dataset per reference
            genome and make that dataset accessible through a Beacon server. If someone queries the server for a
            specific variant that is in our Beacon dataset, the server will reply with
            <i>“Yes, we have seen such a variant”</i>.
        </p>
        <p>
            The user that issued the query then has the possibility to contact a Galaxy server admin who can link the
            variant call in question to particular Galaxy users. If you are among the users that shared the variant, the
            admin will, in turn, contact you and ask if you want to contact the user that initiated the query to
            negotiate further information exchange or data access.
        </p>

        <BAlert v-if="enabled" show>
            <div class="d-flex justify-content-between align-items-center">
                <div>Beacon sharing is <span class="font-weight-bold">enabled</span> for your profile</div>
                <GButton :disabled="togglingBeacon" color="red" @click="toggleBeacon(false)">Disable</GButton>
            </div>
        </BAlert>

        <!-- Setting to show when beacon is disabled -->
        <BAlert v-else show>
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    Beacon sharing is currently <span class="font-weight-bold">disabled</span> - no data will be shared
                </div>
                <GButton :disabled="togglingBeacon" color="green" @click="toggleBeacon(true)">Enable</GButton>
            </div>
        </BAlert>

        <template v-if="enabled">
            <div>
                <p>
                    You can share data by copying VCF or VCF.bgzip files to a history called
                    <i>"{{ BEACON_HISTORY_NAME }}"</i>
                </p>
                <p>
                    The Beacon database is rebuilt periodically. Therefore, changes do not go into effect immediately.
                    If you disable beacon sharing or remove a dataset from the beacon history, the corresponding
                    variants will disappear from the beacon dataset during the next rebuild.
                </p>
            </div>

            <!-- Detailed information about the beacon history -->
            <div class="my-1">
                <!-- Case: History does not exist-->
                <BAlert v-if="!beaconHistories.length" show>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>No beacon history found</div>
                        <GButton color="blue" @click="createBeaconHistory">
                            <FontAwesomeIcon :icon="faPlus" fixed-width />
                            Create Beacon History
                        </GButton>
                    </div>
                </BAlert>

                <div v-else>
                    <Heading separator size="sm">Existing Beacon Histories</Heading>

                    <!-- Case: History exists -->
                    <GTable
                        id="beacon-histories-table"
                        striped
                        :fields="fields"
                        :items="beaconHistories"
                        sort-by="create_time"
                        sort-desc
                        :overlay-loading="loadingHistories">
                        <template v-slot:cell(name)="{ item }">
                            {{ BEACON_HISTORY_NAME }}
                            <span v-if="item.contents_active"> with {{ item.contents_active.active }} datasets </span>
                        </template>
                        <template v-slot:cell(create_time)="{ item }">
                            <UtcDate v-if="item.create_time" :date="item.create_time" mode="elapsed" />
                        </template>
                        <template v-slot:cell(set_current)="{ item }">
                            <GButton
                                class="text-nowrap float-right"
                                color="blue"
                                :disabled="historyOperationRunning || historyStore.currentHistoryId === item.id"
                                :disabled-title="
                                    historyStore.currentHistoryId === item.id ? 'History is current' : undefined
                                "
                                @click="switchHistory(item.id)">
                                <FontAwesomeIcon
                                    :icon="historyOperationRunning ? faSpinner : faExchangeAlt"
                                    fixed-width
                                    :spin="historyOperationRunning" />
                                Switch to History
                            </GButton>
                        </template>
                    </GTable>
                </div>
            </div>

            <div class="mt-3">
                <p>Datasets must fulfill the following conditions in order to be processed</p>
                <ul>
                    <li>must be VCF or VCF.bgzip format</li>
                    <li>must have a human reference assigned to it (e.g. hg19)</li>
                    <li>must define at least one sample in a dedicated genotype column</li>
                    <li>
                        must contain the info field <i>AC</i>, with the total number of alternate alleles in called
                        genotypes
                    </li>
                </ul>
            </div>
        </template>
    </GModal>
</template>
