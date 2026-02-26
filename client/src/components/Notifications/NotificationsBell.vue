<script setup lang="ts">
import { faBell } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { Placement } from "@popperjs/core";
import { BNavItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import type { PropType } from "vue";
import { useRouter } from "vue-router/composables";

import { useNotificationsStore } from "@/stores/notificationsStore";

import Popper from "@/components/Popper/Popper.vue";

defineProps({
    tooltipPlacement: {
        type: String as PropType<Placement>,
        default: "right",
    },
});

const router = useRouter();
const { totalUnreadCount } = storeToRefs(useNotificationsStore());

function onClick() {
    router.push("/user/notifications");
}
</script>

<template>
    <Popper :placement="tooltipPlacement">
        <template v-slot:reference>
            <BNavItem id="activity-notifications" @click="onClick">
                <span class="position-relative">
                    <span v-if="!!totalUnreadCount" class="indicator"> </span>
                    <FontAwesomeIcon class="nav-icon" :icon="faBell" />
                </span>
            </BNavItem>
        </template>
        <div class="px-2 py-1">
            {{
                totalUnreadCount
                    ? `You have ${totalUnreadCount} unread notifications`
                    : "You have no unread notifications"
            }}
        </div>
    </Popper>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.nav-item {
    display: flex;
    align-items: center;
    align-content: center;
    justify-content: center;
}

.nav-icon {
    @extend .nav-item;
    font-size: 1rem;
}

.indicator {
    position: absolute;
    top: -0.2rem;
    right: -0.1rem;
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 50%;
    background: $brand-danger;
}
</style>
