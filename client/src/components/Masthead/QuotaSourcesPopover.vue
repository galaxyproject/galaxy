<script setup lang="ts">
import { ref } from "vue";

import localize from "@/utils/localization";

import GPopover from "@/components/BaseComponents/GPopover.vue";

defineProps<{
    /** Id of the element the popover opens from */
    target: string;
}>();

const isShown = ref(false);
</script>

<template>
    <GPopover
        v-model:show="isShown"
        interactive
        :target="target"
        triggers="hover"
        placement="bottom"
        :title="localize('Storage usage')"
        custom-class="quota-sources-popover">
        <slot :is-shown="isShown" />
    </GPopover>
</template>

<!-- Not scoped: the popover moves itself to the document body -->
<style lang="scss">
.quota-sources-popover {
    min-width: 18rem;
    max-width: 24rem;
}
</style>
