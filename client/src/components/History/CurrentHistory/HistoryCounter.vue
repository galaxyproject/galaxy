<template>
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
    </div>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { formatDistanceToNowStrict } from "date-fns";
import { usesDetailedHistoryMixin } from "./usesDetailedHistoryMixin.js";

export default {
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
    },
    data() {
        return {
            reloadButtonCls: "fa fa-sync",
            reloadButtonTitle: "",
            reloadButtonVariant: "link",
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
    },
};
</script>
