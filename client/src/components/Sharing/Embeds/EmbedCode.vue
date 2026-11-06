<script setup lang="ts">
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import { copy } from "@/utils/clipboard";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = withDefaults(
    defineProps<{
        title: string;
        url: string;
        attributes?: string;
    }>(),
    {
        attributes: " ",
    },
);

const embed = computed(() => `<iframe title="${props.title}"${props.attributes}src="${props.url}"></iframe>`);

const copied = ref(false);

function onCopy() {
    copy(embed.value);
    copied.value = true;
    setTimeout(() => {
        copied.value = false;
    }, 2000);
}
</script>

<template>
    <label for="embed-code" class="w-100">
        Embed code
        <BInputGroup id="embed-code">
            <BFormInput class="embed-code-input" :value="embed" readonly />
            <BInputGroupAppend>
                <GButton color="blue" @click="onCopy">
                    {{ copied ? "Copied!" : "Copy" }}
                </GButton>
            </BInputGroupAppend>
        </BInputGroup>
    </label>
</template>

<style scoped lang="scss">
.embed-code-input {
    background-color: transparent;
    font-family: monospace;
    font-size: 0.875rem;
}
</style>
