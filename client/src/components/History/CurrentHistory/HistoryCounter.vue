<template>
    <div class="history-size my-1 d-flex justify-content-between">
        <b-button
            v-b-tooltip.hover
            title="History Size"
            variant="link"
            size="sm"
            class="rounded-0 text-decoration-none"
            @click="onDashboard">
            <FontAwesomeIcon icon="fa-database" />
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
                <FontAwesomeIcon icon="fa-map-marker" />
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
                <FontAwesomeIcon icon="fa-trash" />
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
                <FontAwesomeIcon icon="fa-eye-slash" />
                <span>{{ numItemsHidden }}</span>
            </b-button>
            <b-button
                v-b-tooltip.hover
                :title="reloadButtonTitle"
                :variant="reloadButtonVariant"
                size="sm"
                class="rounded-0 text-decoration-none"
                @click="reloadContents()">
                <FontAwesomeIcon icon="fa-sync" :spin="reloadButtonSpin" />
            </b-button>
        </b-button-group>
    </div>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { formatDistanceToNowStrict } from "date-fns";
import { usesDetailedHistoryMixin } from "./usesDetailedHistoryMixin.js";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase, faTrash, faEyeSlash, faMapMarker, faSync } from "@fortawesome/free-solid-svg-icons";

library.add(faDatabase, faTrash, faEyeSlash, faMapMarker, faSync);

export default {
    components: { FontAwesomeIcon },
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
            reloadButtonSpin: false,
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
            this.reloadButtonSpin = true;
            setTimeout(() => {
                this.reloadButtonSpin = false;
            }, 1000);
        },
    },
};
</script>
