<!-- menu allowing user to change the current history, make a new one, basically anything that's
"above" editing the current history -->

<template>
    <div>
        <b-dropdown
            size="sm"
            variant="link"
            :text="title | l"
            toggle-class="text-decoration-none"
            class="histories-operation-menu"
            data-description="histories operation menu">
            <template v-slot:button-content>
                <Icon fixed-width class="mr-1" icon="folder" />
                <span class="text-nowrap">{{ title | l }}</span>
            </template>

            <b-dropdown-text>
                <div v-if="userHistoriesLoading">
                    <b-spinner small v-if="userHistoriesLoading" />
                    <span>Fetching histories from server</span>
                </div>
                <span v-else>You have {{ histories.length }} histories.</span>
            </b-dropdown-text>

            <b-dropdown-divider></b-dropdown-divider>

            <b-dropdown-item v-b-modal.history-selector-modal>
                <Icon fixed-width class="mr-1" icon="exchange-alt" />
                <span v-localize>Change History</span>
            </b-dropdown-item>

            <b-dropdown-item data-description="create new history" @click="$emit('createNewHistory')">
                <Icon fixed-width class="mr-1" icon="plus" />
                <span v-localize>Create a New History</span>
            </b-dropdown-item>

            <b-dropdown-item @click="backboneRoute('/histories/list')">
                <Icon fixed-width class="mr-1" icon="list" />
                <span v-localize>View Saved Histories</span>
            </b-dropdown-item>

            <b-dropdown-item
                data-description="switch to multi history view"
                @click="redirect('/history/view_multiple')">
                <Icon fixed-width class="mr-1" icon="columns" />
                <span v-localize>Show Histories Side-by-Side</span>
            </b-dropdown-item>

            <b-dropdown-divider></b-dropdown-divider>

            <b-dropdown-item data-description="switch to legacy history view" @click="switchToLegacyHistoryPanel">
                <Icon fixed-width class="mr-1" icon="arrow-up" />
                <span v-localize>Return to legacy panel</span>
            </b-dropdown-item>
        </b-dropdown>

        <!-- modals -->
        <HistorySelectorModal
            id="history-selector-modal"
            :histories="histories"
            :current-history="currentHistory"
            @selectHistory="$emit('setCurrentHistory', $event)" />
    </div>
</template>

<script>
import { History } from "components/History/model";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { switchToLegacyHistoryPanel } from "components/History/adapters/betaToggle";
import HistorySelectorModal from "components/History/Modals/HistorySelectorModal";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        HistorySelectorModal,
    },
    props: {
        histories: { type: Array, required: true },
        currentHistory: { type: History, required: true },
        title: { type: String, required: false, default: "Histories" },
        userHistoriesLoading: { type: Boolean, required: false, default: false },
    },
    methods: {
        switchToLegacyHistoryPanel,
    },
};
</script>
