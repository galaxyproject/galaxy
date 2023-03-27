<template>
    <CurrentUser v-slot="{ user }">
        <div class="history-size my-1 d-flex justify-content-between">
            <b-button
                v-b-tooltip.hover
                title="History Size"
                variant="link"
                size="sm"
                class="rounded-0 text-decoration-none"
                @click="onDashboard">
                <icon icon="database" />
                <span>{{ historySize | niceFileSize }}</span>
            </b-button>
            <b-button-group>
                <ConfigProvider v-slot="{ config }">
                    <b-button
                        v-if="config && config.object_store_allows_id_selection"
                        :id="`history-storage-${history.id}`"
                        variant="link"
                        size="sm"
                        class="rounded-0 text-decoration-none"
                        @click="showPreferredObjectStoreModal = true">
                        <icon icon="hdd" />
                    </b-button>
                </ConfigProvider>
                <ConfigProvider v-slot="{ config }">
                    <PreferredStorePopover
                        v-if="config && config.object_store_allows_id_selection"
                        :history-id="history.id"
                        :history-preferred-object-store-id="historyPreferredObjectStoreId"
                        :user="user">
                    </PreferredStorePopover>
                </ConfigProvider>
                <b-button-group>
                    <b-button
                        v-b-tooltip.hover
                        title="Show active"
                        variant="link"
                        size="sm"
                        class="rounded-0 text-decoration-none"
                        @click="setFilter('')">
                        <span class="fa fa-map-marker" />
                        <span>{{ numItemsActive }}</span>
                    </b-button>
                    <b-button
                        v-if="numItemsDeleted"
                        v-b-tooltip.hover
                        title="Show deleted"
                        variant="link"
                        size="sm"
                        class="rounded-0 text-decoration-none"
                        @click="setFilter('deleted:true')">
                        <icon icon="trash" />
                        <span>{{ numItemsDeleted }}</span>
                    </b-button>
                    <b-button
                        v-if="numItemsHidden"
                        v-b-tooltip.hover
                        title="Show hidden"
                        variant="link"
                        size="sm"
                        class="rounded-0 text-decoration-none"
                        @click="setFilter('visible:false')">
                        <icon icon="eye-slash" />
                        <span>{{ numItemsHidden }}</span>
                    </b-button>
                    <b-button
                        v-b-tooltip.hover
                        :title="reloadButtonTitle"
                        :variant="reloadButtonVariant"
                        size="sm"
                        class="rounded-0 text-decoration-none"
                        @click="reloadContents()">
                        <span :class="reloadButtonCls" />
                    </b-button>
                </b-button-group>
                <b-modal
                    v-model="showPreferredObjectStoreModal"
                    title="History Preferred Object Store"
                    modal-class="history-preferred-object-store-modal"
                    title-tag="h3"
                    size="sm"
                    hide-footer>
                    <SelectPreferredStore
                        :user-preferred-object-store-id="user.preferred_object_store_id"
                        :history="history"
                        @updated="onUpdatePreferredObjectStoreId" />
                </b-modal>
            </b-button-group>
        </div>
    </CurrentUser>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { formatDistanceToNowStrict } from "date-fns";
import { usesDetailedHistoryMixin } from "./usesDetailedHistoryMixin.js";
import CurrentUser from "components/providers/CurrentUser";
import ConfigProvider from "components/providers/ConfigProvider";
import PreferredStorePopover from "./PreferredStorePopover";
import SelectPreferredStore from "./SelectPreferredStore";

export default {
    components: {
        ConfigProvider,
        CurrentUser,
        PreferredStorePopover,
        SelectPreferredStore,
    },
    filters: {
        niceFileSize(rawSize = 0) {
            return prettyBytes(rawSize);
        },
    },
    mixins: [usesDetailedHistoryMixin],
    props: {
        history: { type: Object, required: true },
        isWatching: { type: Boolean, default: false },
        lastChecked: { type: Date, default: null },
        filterText: { type: String, default: "" },
    },
    data() {
        return {
            reloadButtonCls: "fa fa-sync",
            reloadButtonTitle: "",
            reloadButtonVariant: "link",
            showPreferredObjectStoreModal: false,
            historyPreferredObjectStoreId: this.history.preferred_object_store_id,
        };
    },
    mounted() {
        this.updateTime();
        // update every second
        setInterval(this.updateTime.bind(this), 1000);
    },
    methods: {
        onDashboard() {
            this.$router.push("/storage");
        },
        setFilter(newFilterText) {
            this.$emit("update:filter-text", newFilterText);
        },
        toggleDeleted() {
            if (this.filterText === "deleted:true") {
                this.setFilter("");
            } else {
                this.setFilter("deleted:true");
            }
        },
        toggleHidden() {
            if (this.filterText === "visible:false") {
                this.setFilter("");
            } else {
                this.setFilter("visible:false");
            }
        },
        updateTime() {
            const diffToNow = formatDistanceToNowStrict(this.lastChecked, { addSuffix: true, includeSeconds: true });
            const diffToNowSec = Date.now() - this.lastChecked;
            // if history isn't being watched or hasn't been watched/polled for over 2 minutes
            if (!this.isWatching || diffToNowSec > 120000) {
                this.reloadButtonTitle = "Last refreshed " + diffToNow + ". Consider reloading the page.";
                this.reloadButtonVariant = "danger";
            } else {
                this.reloadButtonTitle = "Last refreshed " + diffToNow;
                this.reloadButtonVariant = "link";
            }
        },
        async reloadContents() {
            this.$emit("reloadContents");
            this.reloadButtonCls = "fa fa-sync fa-spin";
            setTimeout(() => {
                this.reloadButtonCls = "fa fa-sync";
            }, 1000);
        },
        onUpdatePreferredObjectStoreId(preferredObjectStoreId) {
            this.showPreferredObjectStoreModal = false;
            // ideally this would be pushed back to the history object somehow
            // and tracked there... but for now this is only component using
            // this information.
            this.historyPreferredObjectStoreId = preferredObjectStoreId;
        },
    },
};
</script>
