<!-- Layout to house all the extraneous structural markup elements
and non-semantic utility classes that are necessary when you use an
amateur-hour baby-tool like Bootstrap instead of taking the afternoon
to learn how CSS is supposed to work. -->

<template>
    <section class="history beta d-flex flex-column">
        <header>
            <nav class="d-flex justify-content-between bg-secondary">
                <slot name="globalnav">Global Navigation Default</slot>
                <slot name="localnav">Local Navigation Default</slot>
            </nav>

            <!-- details about the thing you're looking at -->
            <div class="px-3 py-4 details">
                <slot name="details"></slot>
            </div>
        </header>

        <!-- warnings, messages, dirty limericks -->
        <section v-if="$slots.messages">
            <slot name="messages"></slot>
        </section>

        <!-- controls atop the list -->
        <section v-if="$slots.listcontrols" class="list-controls">
            <slot name="listcontrols"></slot>
        </section>

        <!-- scrolling list -->
        <section class="position-relative flex-grow-1 scroller">
            <slot name="listing"></slot>
        </section>

        <!-- no dom layout, holds modal markup -->
        <section v-if="$slots.modals">
            <slot name="modals"></slot>
        </section>
    </section>
</template>

<style lang="scss">
.history.beta {
    /* TODO: css reset? */
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        margin: 0;
    }

    .list-controls {
        margin-bottom: 2px;
    }

    .list-controls:empty,
    .messages:empty {
        display: none;
    }
}
</style>
