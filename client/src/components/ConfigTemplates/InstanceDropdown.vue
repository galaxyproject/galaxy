<script setup lang="ts">
import { faArrowUp, faCaretDown, faEdit, faStethoscope, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useRouter } from "vue-router/composables";

interface Props {
    prefix: string;
    name: string;
    routeEdit: string;
    routeUpgrade: string;
    isUpgradable: boolean;
}

const router = useRouter();

defineProps<Props>();

const emit = defineEmits<{
    (e: "remove"): void;
    (e: "test"): void;
}>();
</script>

<template>
    <div>
        <button
            id="instance-operations"
            :class="`${prefix}-instance-dropdown`"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            class="ui-link font-weight-bold text-nowrap">
            <FontAwesomeIcon :icon="faCaretDown" size="lg" />
            <span class="instance-dropdown-name font-weight-bold">{{ name }}</span>
        </button>
        <div class="dropdown-menu" :aria-labelledby="`${prefix}-instance-dropdown`">
            <button
                v-if="isUpgradable"
                class="dropdown-item"
                :href="routeUpgrade"
                @keypress="router.push(routeUpgrade)"
                @click.prevent="router.push(routeUpgrade)">
                <FontAwesomeIcon :icon="faArrowUp" />
                <span v-localize>升级</span>
            </button>
            <button
                class="dropdown-item"
                :href="routeEdit"
                @keypress="router.push(routeEdit)"
                @click.prevent="router.push(routeEdit)">
                <FontAwesomeIcon :icon="faEdit" />
                <span v-localize>编辑配置</span>
            </button>
            <button class="dropdown-item" @keypress="emit('test')" @click.prevent="emit('test')">
                <FontAwesomeIcon :icon="faStethoscope" />
                <span v-localize>测试实例</span>
            </button>
            <button class="dropdown-item" @keypress="emit('remove')" @click.prevent="emit('remove')">
                <FontAwesomeIcon :icon="faTrash" />
                <span v-localize>移除实例</span>
            </button>
        </div>
    </div>
</template>
