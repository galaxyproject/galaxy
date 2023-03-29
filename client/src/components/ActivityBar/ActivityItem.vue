<script setup lang="ts">
import { ref } from "vue";
import Popper from "./Popper.vue";

export interface Props {
    id: string;
    title: string;
    icon?: string;
    isActive?: boolean;
    tooltip?: string;
    progressPercentage: number;
    progressStatus: string;
}

const props = withDefaults(defineProps<Props>(), {
    icon: "question",
    isActive: false,
    tooltip: null,
});

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <div>
        <Popper reference-is="span" popper-is="span" placement="right">
            <template #reference>
                <b-nav-item
                    :id="id"
                    class="position-relative mb-1"
                    :class="{ 'nav-item-active': isActive }"
                    :aria-label="title | l"
                    @click="emit('click')">
                    <template>
                        <span v-if="!!progressStatus" class="progress">
                            <div
                                class="progress-bar notransition"
                                :class="{
                                    'bg-danger': progressStatus === 'danger',
                                    'bg-success': progressStatus === 'success',
                                }"
                                :style="{
                                    width: `${progressPercentage}%`,
                                }" />
                        </span>
                        <span class="position-relative">
                            <div class="nav-icon">
                                <Icon :icon="icon" />
                            </div>
                            <div class="nav-title">{{ title }}</div>
                        </span>
                    </template>
                </b-nav-item>
            </template>
            <div style="background: red; width: 10rem">{{ tooltip | l }}</div>
        </Popper>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.nav-item {
    display: flex;
    align-items: center;
    align-content: center;
    justify-content: center;
}

.nav-item-active {
    border-radius: $border-radius-extralarge;
    background: $gray-300;
}

.nav-icon {
    @extend .nav-item;
    font-size: 1rem;
}

.nav-title {
    @extend .nav-item;
    margin-top: 0.7rem;
    margin-bottom: 0.3rem;
    line-height: 0rem;
    font-size: 0.7rem;
}

.progress {
    border-radius: $border-radius-extralarge;
    position: absolute;
    width: 100%;
    height: 100%;
    left: 0;
    top: 0;
}

.notransition {
    -webkit-transition: none;
    -moz-transition: none;
    -ms-transition: none;
    -o-transition: none;
    transition: none;
}
</style>
