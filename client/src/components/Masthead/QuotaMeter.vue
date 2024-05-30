<template>
    <div v-b-tooltip.hover.bottom class="quota-meter d-flex align-items-center" title="Storage and Usage Details">
        <b-link class="quota-progress" to="/storage" data-description="storage dashboard link">
            <b-progress :max="100">
                <b-progress-bar aria-label="Quota usage" :value="usage" :variant="variant" />
            </b-progress>
            <span v-if="hasQuota">{{ usingString + " " + usage.toFixed(0) }}%</span>
            <span v-else>{{ usingString + " " + totalUsageString }}</span>
        </b-link>
    </div>
</template>

<script>
import { mapState } from "pinia";
import { bytesToString } from "utils/utils";

import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

export default {
    name: "QuotaMeter",
    data() {
        return {
            usingString: this.l("Using"),
        };
    },
    computed: {
        ...mapState(useConfigStore, ["config"]),
        ...mapState(useUserStore, ["currentUser"]),
        hasQuota() {
            const quotasEnabled = this.config?.enable_quotas ?? false;
            const quotaLimited = this.currentUser?.quota !== "unlimited" ?? false;
            return quotasEnabled && quotaLimited;
        },
        usage() {
            if (this.hasQuota) {
                return this.currentUser?.quota_percent ?? 0;
            } else {
                return this.currentUser?.total_disk_usage ?? 0;
            }
        },
        totalUsageString() {
            const total = this.currentUser?.total_disk_usage ?? 0;
            return bytesToString(total, true);
        },
        variant() {
            if (!this.hasQuota || this.usage < 80) {
                return "success";
            } else if (this.usage < 95) {
                return "warning";
            } else {
                return "danger";
            }
        },
    },
};
</script>

<style lang="scss" scoped>
.quota-meter {
    position: relative;
    height: 100%;
    margin-left: 0.5rem;
    margin-right: 0.5rem;
    .quota-progress {
        width: 150px;
        height: 1.4em;
        position: relative;
        & > * {
            position: absolute;
            width: 100%;
            height: 100%;
            text-align: center;
        }
        & > span {
            line-height: 1.4em;
            pointer-events: none;
        }
    }
    :deep(a) {
        &:focus-visible {
            outline: 2px solid var(--masthead-text-hover);
        }
    }
}
</style>
