<template>
    <section class="history-layout d-flex flex-column">
        <header>
            <!-- navigation bar at the top-->
            <nav class="d-flex justify-content-between bg-secondary">
                <slot name="navigation" />
            </nav>

            <!-- details about the thing you're looking at -->
            <div class="px-3 py-4 details">
                <slot name="details" />
            </div>
        </header>

        <!-- warnings, messages -->
        <section v-if="$slots.messages">
            <slot name="messages" />
        </section>

        <!-- controls above list -->
        <section v-if="$slots.listcontrols" class="list-controls">
            <slot name="listcontrols" />
        </section>

        <!-- scrolling list -->
        <section class="position-relative flex-grow-1 scroller">
            <slot name="listing" />
        </section>

        <!-- no dom layout, holds modal markup -->
        <section v-if="$slots.modals">
            <slot name="modals" />
        </section>
    </section>
</template>

<style lang="scss">
.history-layout {
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        margin: 0;
    }
    .list-controls:empty,
    .messages:empty {
        display: none;
    }
}
</style>
