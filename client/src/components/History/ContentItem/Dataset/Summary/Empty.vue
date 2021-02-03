<template functional>
    <div v-if="props.dataset">
        <span v-localize>No data</span>: <i>{{ props.dataset.misc_blurb }}</i>
    </div>
</template>
