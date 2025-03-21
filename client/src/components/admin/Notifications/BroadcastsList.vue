<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faClock, faHourglassHalf, faRedo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchAllBroadcasts, updateBroadcast } from "@/api/notifications.broadcast";
import { Toast } from "@/composables/toast";
import { type BroadcastNotification } from "@/stores/broadcastsStore";

import BroadcastCard from "./BroadcastCard.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCheck, faClock, faHourglassHalf, faRedo);

const router = useRouter();

const overlay = ref(false);
const loading = ref(false);
const showActive = ref(true);
const showExpired = ref(true);
const showScheduled = ref(true);
const broadcasts = ref<BroadcastNotification[]>([]);

const filteredBroadcasts = computed(() => {
    return broadcasts.value.filter(filterBroadcasts);
});

const broadcastExpired = (item: BroadcastNotification) =>
    item.expiration_time && new Date(item.expiration_time) < new Date();

function filterBroadcasts(item: BroadcastNotification) {
    if (broadcastExpired(item)) {
        return showExpired.value;
    }
    if (broadcastPublished(item)) {
        return showActive.value;
    }
    return showScheduled.value;
}

function broadcastPublished(item: BroadcastNotification) {
    return new Date(item.publication_time) < new Date();
}

function onEdit(item: BroadcastNotification) {
    router.push(`/admin/notifications/edit_broadcast/${item.id}`);
}

async function onForceExpire(item: BroadcastNotification) {
    await updateBroadcast(item.id, { expiration_time: new Date().toISOString().slice(0, 23) });
    await loadBroadcastsList(true);
    Toast.info("广播已标记为过期。它将在下一个清理周期中从数据库中删除。");
}

function onGoToLink(link: string) {
    if (link.startsWith("/")) {
        router.push(link);
    } else {
        window.open(link, "_blank");
    }
}

async function loadBroadcastsList(overlayLoading = false) {
    if (overlayLoading) {
        overlay.value = true;
    } else {
        loading.value = true;
    }

    try {
        broadcasts.value = await fetchAllBroadcasts();
        broadcasts.value.sort((a, b) => new Date(b.create_time).getTime() - new Date(a.create_time).getTime());
    } finally {
        loading.value = false;
        overlay.value = false;
    }
}

loadBroadcastsList();
</script>

<template>
    <div>
        <Heading h2 class="mb-2"> 广播列表 </Heading>
        <p v-localize class="mb-2">
            广播是显示给所有用户的通知。它们可以安排在特定时间发布，也可以设置在特定时间过期。广播还可以标记为紧急，以使其更突出。
        </p>
        <p class="mb-2">
            <b>注意：</b> 过期的广播将在定期清理过程中从数据库中完全删除。清理间隔在 Galaxy 配置文件中的 
            <code>expired_notifications_cleanup_interval</code> 键下定义。
        </p>

        <div class="list-operations mb-2">
            <BRow class="align-items-center" no-gutters>
                <BCol class="ml-2">
                    <BRow align-h="start" align-v="center">
                        <span class="mx-2"> 筛选器: </span>
                        <BButtonGroup>
                            <BButton
                                id="show-active-filter-button"
                                size="sm"
                                :pressed="showActive"
                                title="显示活跃广播"
                                variant="outline-primary"
                                @click="showActive = !showActive">
                                <FontAwesomeIcon :icon="faCheck" />
                                活跃
                            </BButton>
                            <BButton
                                id="show-scheduled-filter-button"
                                size="sm"
                                :pressed="showScheduled"
                                title="显示计划广播"
                                variant="outline-primary"
                                @click="showScheduled = !showScheduled">
                                <FontAwesomeIcon :icon="faClock" />
                                计划
                            </BButton>
                            <BButton
                                id="show-expired-filter-button"
                                size="sm"
                                :pressed="showExpired"
                                title="显示过期广播"
                                variant="outline-primary"
                                @click="showExpired = !showExpired">
                                <FontAwesomeIcon :icon="faHourglassHalf" />
                                过期
                            </BButton>
                        </BButtonGroup>
                    </BRow>
                </BCol>
                <BCol>
                    <BRow align-h="end" align-v="center" no-gutters>
                        <BButton
                            v-b-tooltip.hover
                            size="sm"
                            :disabled="loading || overlay"
                            variant="outline-primary"
                            title="刷新广播"
                            @click="loadBroadcastsList">
                            <FontAwesomeIcon :icon="faRedo" />
                        </BButton>
                    </BRow>
                </BCol>
            </BRow>
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="加载广播" />
        </BAlert>

        <BAlert v-else-if="filteredBroadcasts.length === 0" id="empty-broadcast-list-alert" variant="info" show>
            没有要显示的广播通知。请使用上面的按钮创建新的广播通知或更改筛选器。
        </BAlert>
        <BOverlay v-else :show="overlay" rounded="sm">
            <BroadcastCard
                v-for="notification in filteredBroadcasts"
                :key="notification.id"
                :broadcast-notification="notification"
                data-test-id="broadcast-item"
                @edit="onEdit"
                @expire="onForceExpire"
                @go-to-link="onGoToLink" />
        </BOverlay>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.list-operations {
    border-radius: 0.5rem;
    border: 1px solid $gray-400;
    padding: 0.5rem;
}
</style>
