<template>
    <UserPreferencesElement
        title="Manage Beacon"
        :icon="faBroadcastTower"
        description="Contribute variants to Beacon"
        @click="openModal">
        <BModal
            id="modal-beacon"
            ref="modal"
            size="xl"
            ok-only
            title="Manage Beacon"
            title-tag="h1"
            @show="onOpenModal">
            <!-- Explanation text-->
            <p>
                The
                <a href="https://beacon-project.io">Global Alliance for Genomics & Health Beacon Project</a> enables
                safe sharing of human genetic variants.<br />
                <br />
                Galaxy lets you use the Beacon protocol to share genetic variants directly from your analysis with the
                scientific community in the following anonymous way:<br />
                <br />
                For participating users, we will merge variant lists to be shared into a single Beacon dataset per
                reference genome and make that dataset accessible through a Beacon server.<br />
                If someone queries the server for a specific variant that is in our Beacon dataset, the server will
                reply with
                <span class="cursive">“Yes, we have seen such a variant”</span>.<br />
                <br />
                The user that issued the query then has the possibility to contact a Galaxy server admin who can link
                the variant call in question to particular Galaxy users. If you are among the users that shared the
                variant, the admin will, in turn, contact you and ask if you want to contact the user that initiated the
                query to negotiate further information exchange or data access.
            </p>

            <BAlert v-if="enabled" show>
                <div class="flex-row space-between">
                    <div class="no-shrink">Beacon sharing is <span class="bold">enabled</span> for your profile</div>
                    <div class="fill"></div>
                    <div class="no-shrink">
                        <BButton variant="danger" @click="optOut">Disable</BButton>
                    </div>
                </div>
            </BAlert>

            <!-- Setting to show when beacon is disabled -->
            <BAlert v-if="!enabled" show>
                <div class="flex-row space-between">
                    <div class="no-shrink">
                        Beacon sharing is currently <span class="bold">disabled</span> - no data will be shared
                    </div>
                    <div class="fill"></div>
                    <div>
                        <BButton variant="success" @click="optIn">Enable</BButton>
                    </div>
                </div>
            </BAlert>

            <div v-if="enabled">
                <p>
                    You can share data by copying VCF or VCF.bgzip files to a history called
                    <span class="cursive gray-background">{{ beaconHistoryName }}</span
                    >. <br />
                    <br />
                    The Beacon database is rebuilt periodically. Therefore, changes do not go into effect immediately.
                    If you disable beacon sharing or remove a dataset from the beacon history, the corresponding
                    variants will disappear from the beacon dataset during the next rebuild.
                </p>
            </div>

            <!-- Detailed information about the beacon history -->
            <div v-if="enabled" class="gray-box">
                <!-- Case: History does not exist-->
                <div v-if="beaconHistories.length < 1" class="flex-row history-entry">
                    <div class="no-shrink">No beacon history found</div>
                    <div class="fill"></div>
                    <div class="no-shrink">
                        <BButton @click="createBeaconHistory">Create Beacon History</BButton>
                    </div>
                </div>

                <!-- Case: History exists -->
                <div
                    v-for="beaconHistory in beaconHistories"
                    :key="beaconHistory.id"
                    class="flex-row history-entry"
                    :class="{
                        'gray-border-bottom': beaconHistory.id !== beaconHistories[beaconHistories.length - 1].id,
                    }">
                    <div v-if="beaconHistory.contents" class="no-shrink">
                        History with {{ beaconHistory.contents.length }} datasets
                    </div>
                    <div class="fill"></div>
                    <div class="no-shrink">
                        <BButton @click="switchHistory(beaconHistory.id)">Switch to History</BButton>
                    </div>
                </div>
            </div>

            <div v-if="enabled">
                <p>Datasets must fulfill the following conditions in order to be processed</p>
                <ul>
                    <li>must be VCF or VCF.bgzip format</li>
                    <li>must have a human reference assigned to it (e.g. hg19)</li>
                    <li>must define at least one sample in a dedicated genotype column</li>
                    <li>
                        must contain the info field <span class="cursive">AC</span>, with the total number of alternate
                        alleles in called genotypes
                    </li>
                </ul>
            </div>
        </BModal>
    </UserPreferencesElement>
</template>

<script>
import { faBroadcastTower } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { BAlert, BButton, BModal } from "bootstrap-vue";
import { mapActions } from "pinia";
import { withPrefix } from "utils/redirect";

import { useHistoryStore } from "@/stores/historyStore";

import UserPreferencesElement from "./UserPreferencesElement.vue";

export default {
    components: { BButton, BModal, UserPreferencesElement, BAlert },
    props: {
        userId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            enabled: false,
            beaconHistoryName: "Beacon Export 📡",
            beaconHistories: [{}],
            faBroadcastTower,
        };
    },
    methods: {
        ...mapActions(useHistoryStore, ["setCurrentHistory"]),
        switchHistory: async function (historyId) {
            await this.setCurrentHistory(historyId);
        },
        getBeaconHistories: function () {
            axios
                .get(withPrefix("api/histories?&keys=id,contents&q=name&qv=" + encodeURI(this.beaconHistoryName)))
                .then((response) => {
                    this.beaconHistories = this.removeDeletedContents(response.data);
                })
                .catch((error) => {
                    console.log(error.response);
                });
        },
        removeDeletedContents: function (beaconHistories) {
            beaconHistories.forEach((beaconHistory) => {
                beaconHistory.contents.splice(
                    0,
                    beaconHistory.contents.length,
                    ...beaconHistory.contents.filter((dataset) => {
                        return !dataset.deleted;
                    })
                );
            });
            return beaconHistories;
        },
        createBeaconHistory: function () {
            const annotation =
                "Variants will be collected from VCF datasets in this history if beacon sharing is activated";
            axios
                .post(withPrefix("api/histories"), { name: this.beaconHistoryName })
                .then((response) => {
                    axios.put(withPrefix(`api/histories/${response.data.id}`), { annotation: annotation }).then(() => {
                        this.getBeaconHistories();
                    });
                })
                .catch((error) => {
                    this.errorMessages.push(error.response.data.err_msg), console.log(error.response);
                });
        },
        optIn() {
            try {
                axios.post(withPrefix(`api/users/${this.userId}/beacon`), { enabled: true }).then((response) => {
                    // TODO check response
                    this.loadSettings();
                    if (this.beaconHistories.length < 1) {
                        this.createBeaconHistory();
                        this.getBeaconHistories();
                    }
                });
            } catch (e) {
                console.log(e);
            }
        },
        optOut() {
            try {
                axios.post(withPrefix(`api/users/${this.userId}/beacon`), { enabled: false }).then((response) => {
                    // TODO check response
                    this.loadSettings();
                });
            } catch (e) {
                console.log(e);
            }
        },
        openModal() {
            this.$refs.modal.show();
        },
        onOpenModal() {
            this.loadSettings();
            this.getBeaconHistories();
        },
        async loadSettings() {
            try {
                await axios.get(withPrefix(`api/users/${this.userId}/beacon`)).then((response) => {
                    this.enabled = response.data.enabled;
                });
            } catch (e) {
                console.log(e);
            }
        },
    },
};
</script>

<style scoped>
span.bold {
    font-weight: bold;
}

.pref-icon {
    width: 3rem;
}

.gray-box {
    margin-top: 32px;
    margin-bottom: 32px;
    border: 1px solid #bdc6d0;
    border-radius: 5px;
    background-color: rgba(0, 0, 0, 0.04);
}

.flex-row {
    display: flex;
    flex-flow: row;
}

.history-entry {
    padding: 8px;
}

.gray-border-bottom {
    border-bottom: 1px solid #bdc6d0;
}

.space-between {
    justify-content: space-between;
    align-items: center;
}

.cursive {
    font-style: italic;
}

.bold {
    font-weight: bolder;
}

.fill {
    width: 100%;
}

.no-shrink {
    flex-shrink: 0;
}
</style>
