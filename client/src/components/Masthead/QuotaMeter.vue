<template>
    <current-user>
        <div class="quota-meter d-flex align-items-center">
            <b-link v-if="!hasQuota" v-b-tooltip.hover.left to="/storage" class="ml-auto quota-text" :title="title">
                {{ usingString + " " + totalUsageString }}
            </b-link>
            <b-link v-else v-b-tooltip.hover.left class="quota-progress" to="/storage" :title="title">
                <b-progress :max="100">
                    <b-progress-bar aria-label="Quota usage" :value="usage" :variant="variant" />
                </b-progress>
                <span>{{ usingString + " " + usage.toFixed(0) }}%</span>
            </b-link>
        </div>
    </current-user>
</template>

<script>
import { bytesToString } from "utils/utils";
import CurrentUser from "components/providers/CurrentUser";
import { mapGetters } from "vuex";

export default {
    name: "QuotaMeter",
    components: {
        CurrentUser,
    },
    data() {
        return {
            usingString: this.l("Using"),
        };
    },
    computed: {
        ...mapGetters("config", ["config"]),
        ...mapGetters("user", ["currentUser"]),
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
            if (this.currentUser.isAnonymous) {
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
.quota-meter {
    position: relative;
    right: 0.8rem;
    width: 100px;
    height: 100%;

    .quota-progress {
        width: 100%;
        height: 16px;
        position: relative;

        & > * {
            position: absolute;
            width: 100%;
            height: 100%;
            text-align: center;
        }

        & > span {
            line-height: 1em;
            pointer-events: none;
        }
    }

    .quota-text {
        color: var(--masthead-text-color);
        text-decoration: none;
    }

    :deep(a) {
        &:focus-visible {
            outline: 2px solid var(--masthead-text-hover);
        }
    }
}
</style>
