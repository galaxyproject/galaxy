<script setup>
import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faCheckSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

defineProps({
    title: {
        type: String,
        required: true,
    },
    value: {
        type: Boolean,
        required: true,
    },
});

const emit = defineEmits("click");
</script>

<template>
    <tr @click="emit('click')">
        <td>
            <FontAwesomeIcon v-if="value" class="px-2" :icon="faCheckSquare" fa-fw />
            <FontAwesomeIcon v-else class="px-2" :icon="faSquare" fa-fw />
        </td>
        <td class="text-left">
            <span v-localize class="pr-2">{{ title }}</span>
        </td>
    </tr>
</template>
