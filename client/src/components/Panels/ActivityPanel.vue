<script setup lang="ts">
interface Props {
    title: string;
    goToAllTitle?: string;
    href?: string;
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
            :to="props.href"
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
    padding: 0.5rem 1rem;
    background-color: $brand-light;

    .activity-panel-header {
        padding-bottom: 0.5rem;

        .activity-panel-header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 2rem;

            .activity-panel-heading {
                margin: 0;
            }
        }
    }

    .activity-panel-body {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        overflow-y: hidden;
        button:first-child {
            background: none;
            border: none;
            text-align: left;
            transition: none;
            width: 100%;
            border-color: transparent;
        }
        button:first-child:hover {
            background: $brand-primary;
            color: $brand-light;
        }
    }

    .activity-panel-footer {
        margin-top: 0.5rem;
        font-weight: bold;
    }
}
</style>
