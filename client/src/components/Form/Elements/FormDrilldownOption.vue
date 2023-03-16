<script setup lang="ts">
import { computed, ref } from "vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

export interface FormDrilldownProps {
    options: Array<Option>;
    handleClick: Function;
}

const props = defineProps<FormDrilldownProps>();

const showChildren = ref(false);

const hasOptions = computed(() => {
    return props.options.length > 0;
});

function toggleChildren() {
    showChildren.value = !showChildren.value;
}
</script>

<template>
    <div>
        <ul v-for="option in options" :key="option.name" class="ui-drilldown">
            <li>
                <span
                    v-if="hasOptions"
                    @click="toggleChildren"
                    :class="{ 'fa fa-plus-square': !showChildren, 'fa fa-minus-square': showChildren }" />
                <b-form-checkbox class="d-inline" />
                {{ option.name }}
                <form-drilldown-option v-show="showChildren" :options="option.options" :handle-click="handleClick" />
            </li>
        </ul>
    </div>
</template>

<style>
    .ui-drilldown {
        list-style-type: none;
    }
</style>