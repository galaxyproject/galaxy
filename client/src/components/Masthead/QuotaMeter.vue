<template>
    <div class="small-quota-meter d-flex align-items-center">
        <b-link v-if="hasQuota" v-b-tooltip.hover.left class="quota-progress" to="/storage" :title="title">
            <b-progress :value="usage" :max="100" :variant="variant" />
            <span>{{ usingString + " " + usage.toFixed(0) }}%</span>
        </b-link>
        <b-link v-else v-b-tooltip.hover.left :title="title" to="/storage">
            {{ usingString + " " + totalUsageString }}
        </b-link>
    </div>
</template>

<script>
import { bytesToString } from "utils/utils";
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
        ...mapGetters("user", ["currentUser"]),
        hasQuota() {
            return this.config?.enable_quotas ?? false;
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

            return this.usingString + " " + this.totalUsageString + ". " + details;
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
.small-quota-meter {
    position: absolute;
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
}
</style>
