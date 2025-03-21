<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";

import BroadcastsList from "@/components/admin/Notifications/BroadcastsList.vue";
import Heading from "@/components/Common/Heading.vue";

const router = useRouter();
const { config, isConfigLoaded } = useConfig();

function goToCreateNewNotification() {
    router.push("/admin/notifications/create_new_notification");
}

function goToCreateNewBroadcast() {
    router.push("/admin/notifications/create_new_broadcast");
}
</script>

<template>
    <div aria-labelledby="notifications-managements">
        <Heading id="notifications-title" h1 separator inline class="flex-grow-1">
            通知和广播
        </Heading>

        <p>
            作为管理员，您可以向用户（组或角色）发送单独的通知，或者向所有用户（甚至匿名用户）显示
            <i>广播通知</i>。
        </p>

        <div v-if="isConfigLoaded && config.enable_notification_system">
            <div>
                <BButton
                    id="send-notification-button"
                    class="mb-2"
                    variant="outline-primary"
                    @click="goToCreateNewNotification">
                    <FontAwesomeIcon icon="plus" />
                    发送新通知
                </BButton>

                <BButton
                    id="create-broadcast-button"
                    class="mb-2"
                    variant="outline-primary"
                    @click="goToCreateNewBroadcast">
                    <FontAwesomeIcon icon="plus" />
                    创建新广播
                </BButton>
            </div>

            <BroadcastsList class="mt-2" />
        </div>
        <BAlert v-else variant="warning" show>
            通知系统已禁用。要启用它，请在 Galaxy 配置文件中将
            <code>enable_notification_system</code> 选项设置为 <code>true</code>。
        </BAlert>
    </div>
</template>