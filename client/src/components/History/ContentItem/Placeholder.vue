<template>
    <div class="collapsed" data-state="waiting">
        <nav class="content-top-menu d-flex align-items-center justify-content-between p-1">
            <h5 class="flex-grow-1 overflow-hidden mr-auto text-nowrap text-truncate">
                <span class="name">Placholder: {{ item.hid }}</span>
            </h5>
        </nav>
    </div>
</template>

<script>
export default {
    props: {
        item: { type: Object, required: true },
        index: { type: Number, required: true },
    },
};
</script>
