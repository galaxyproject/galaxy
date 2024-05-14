<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowUp, faCaretDown, faEdit, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

interface Props {
    prefix: string;
    name: string;
    routeEdit: string;
    routeUpgrade: string;
    isUpgradable: boolean;
}

library.add(faArrowUp, faCaretDown, faEdit, faTrash);

const title = "";

const router = useRouter();

defineProps<Props>();

const emit = defineEmits<{
    (e: "remove"): void;
}>();
</script>

<template>
    <div>
        <BLink
            v-b-tooltip.hover
            :class="`${prefix}-instance-dropdown font-weight-bold`"
            data-toggle="dropdown"
            :title="title"
            aria-haspopup="true"
            aria-expanded="false">
            <FontAwesomeIcon icon="caret-down" />
            <span class="instance-dropdown-name">{{ name }}</span>
        </BLink>
        <div class="dropdown-menu" :aria-labelledby="`${prefix}-instance-dropdown`">
            <a
                v-if="isUpgradable"
                class="dropdown-item"
                :href="routeUpgrade"
                @keypress="router.push(routeUpgrade)"
                @click.prevent="router.push(routeUpgrade)">
                <FontAwesomeIcon icon="arrowUp" />
                <span v-localize>Upgrade</span>
            </a>
            <a
                class="dropdown-item"
                :href="routeEdit"
                @keypress="router.push(routeEdit)"
                @click.prevent="router.push(routeEdit)">
                <FontAwesomeIcon icon="edit" />
                <span v-localize>Edit configuration</span>
            </a>
            <a class="dropdown-item" @keypress="emit('remove')" @click.prevent="emit('remove')">
                <FontAwesomeIcon icon="trash" />
                <span v-localize>Remove instance</span>
            </a>
        </div>
    </div>
</template>
