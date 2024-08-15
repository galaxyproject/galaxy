<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBell } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BNavItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router/composables";

import { useNotificationsStore } from "@/stores/notificationsStore";

import Popper from "components/Popper/Popper.vue";

library.add(faBell);

defineProps({
    tooltipPlacement: {
        type: String,
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
@import "theme/blue.scss";

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
