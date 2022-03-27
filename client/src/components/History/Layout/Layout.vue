<template>
    <section class="history-layout d-flex flex-column">
        <header>
            <!-- navigation bar at the top-->
            <slot name="navigation" />

            <!-- details about the thing you're looking at -->
            <div class="m-3 details">
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
