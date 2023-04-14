<template>
    <div>
        <div v-if="!hasQuota" class="quota-text d-flex align-items-center">
            <b-link v-b-tooltip.hover.left to="/storage" class="ml-auto" :title="title">
                {{ usingString + " " + totalUsageString }}
            </b-link>
        </div>
        <div v-else class="quota-meter d-flex align-items-center">
            <b-link v-b-tooltip.hover.left class="quota-progress" to="/storage" :title="title">
                <b-progress :max="100">
                    <b-progress-bar aria-label="Quota usage" :value="usage" :variant="variant" />
                </b-progress>
                <span>{{ usingString + " " + usage.toFixed(0) }}%</span>
            </b-link>
        </div>
    </div>
</template>

<script>
import { mapState } from "pinia";
import { bytesToString } from "utils/utils";
import { useUserStore } from "@/stores/userStore";
import { mapGetters } from "vuex";

export default {
    name: "QuotaMeter",
    data() {
        return {
            usingString: this.l("Using"),
        };
    },
    computed: {
        ...mapGetters("config", ["config"]),
        ...mapState(useUserStore, ["currentUser", "isAnonymous"]),
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
        title() {
            let details = "";
            if (this.isAnonymous) {
                details = this.l("Log in for details.");
            } else {
                details = this.l("Click for details.");
            }

            if (this.hasQuota) {
                return this.usingString + " " + this.totalUsageString + ". " + details;
            } else {
                return details;
            }
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
.quote-container {
    position: relative;
    height: 100%;
    margin-right: 0.5rem;
}
.quota-text {
    @extend .quote-container;
    background: var(--masthead-link-color);
    padding-right: 0.5rem;
    padding-left: 0.5rem;
    a {
        color: var(--masthead-text-color);
        text-decoration: none;
    }
}
.quota-meter {
    @extend .quote-container;
    .quota-progress {
        width: 100px;
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
