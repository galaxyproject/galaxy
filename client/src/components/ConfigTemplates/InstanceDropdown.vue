<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
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

library.add(faCaretDown);

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
                @keypress="router.push(routeUpgrade)"
                @click.prevent="router.push(routeUpgrade)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Upgrade</span>
            </a>
            <a class="dropdown-item" @keypress="router.push(routeEdit)" @click.prevent="router.push(routeEdit)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Edit configuration</span>
            </a>
            <a class="dropdown-item" @keypress="emit('remove')" @click.prevent="emit('remove')">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Remove instance</span>
            </a>
        </div>
    </div>
</template>
