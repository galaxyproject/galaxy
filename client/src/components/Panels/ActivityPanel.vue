<script setup lang="ts">
interface Props {
    title: string;
    goToAllTitle?: string;
}

const props = defineProps<Props>();

const emit = defineEmits(["goToAll"]);
</script>

<template>
    <div class="activity-panel" :data-description="props.title" aria-labelledby="activity-panel-heading">
        <div class="activity-panel-header">
            <nav unselectable="on" class="activity-panel-header-top">
                <h2 id="activity-panel-heading" v-localize class="activity-panel-heading h-sm">{{ props.title }}</h2>

                <slot name="header-buttons" />
            </nav>

            <slot name="header" class="activity-panel-header-description" />
        </div>

        <div class="activity-panel-body">
            <slot />
        </div>

        <BButton
            v-if="props.goToAllTitle"
            class="activity-panel-footer"
            variant="primary"
            :data-description="`props.mainButtonText button`"
            @click="emit('goToAll')">
            {{ props.goToAllTitle }}
        </BButton>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.activity-panel {
    height: 100%;
    display: flex;
    flex-flow: column;
    padding: 0.5rem 0.25rem;
    background-color: $brand-light;

    .activity-panel-header {
        padding-bottom: 0.5rem;

        .activity-panel-header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;

            .activity-panel-heading {
                margin: 0 !important;
            }
        }
    }

    .activity-panel-body {
        flex-grow: 1;
        height: 100%;
        overflow-y: auto;
        padding: 0.2rem 0.2rem;
    }

    .activity-panel-footer {
        margin-top: 0.5rem;
    }
}
</style>
