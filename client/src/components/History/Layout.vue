<!-- Layout to house all the extraneous structural markup elements
and non-semantic utility classes that are necessary when you use an
amateur-hour baby-tool like Bootstrap instead of taking the afternoon
to learn how CSS is supposed to work. -->

<template>
    <section class="history d-flex flex-column">
        <header class="p-2">
            <!-- optional slot for injecting global navigation -->
            <nav v-if="$slots.nav" class="top-nav pb-2">
                <slot name="nav"></slot>
            </nav>
            <!-- details about the thing you're looking at -->
            <slot name="details"></slot>
        </header>

        <!-- warnings, messages, dirty limericks -->
        <section v-if="$slots.messages">
            <slot name="messages"></slot>
        </section>

        <!-- controls atop the list -->
        <section v-if="$slots.listcontrols" class="p-2">
            <slot name="listcontrols"></slot>
        </section>

        <!-- scrolling list -->
        <section class="scroller flex-grow-1">
            <slot name="listing"></slot>
        </section>

        <!-- no dom layout, holds modal markup -->
        <section v-if="$slots.modals">
            <slot name="modals"></slot>
        </section>
    </section>
</template>

<style lang="scss">
@import "scss/mixins.scss";
@import "scss/transitions.scss";
@import "scss/loadingBackground.scss";

/* TODO: css reset? */

.history {
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        margin: 0;
    }
}

/*
container css for first child of top-nav,
flex horizontally

Vue can't put in multi-root slot contents so we have to do some kung-fu to get
the layout right on the top-nav. There will have to be an extra div container
around the contents of the nav slot, so we'll style that right here so the user
doesn't need to do it manually every time. */

.history > header > .top-nav > * {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
}

.history .messages:empty {
    display: none;
}

/* make sure scroller actually scrolls */

.history .scroller {
    position: relative;
}
</style>
