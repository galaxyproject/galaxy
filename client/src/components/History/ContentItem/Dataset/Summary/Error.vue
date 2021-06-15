<template functional>
    <div v-if="props.dataset">
        <div v-if="!props.dataset.purged && props.dataset.misc_info">
            <span>{{ props.dataset.misc_info }}</span>
        </div>
        <span class="help-text" v-localize>An error occurred with this props.dataset</span>
        <div v-if="props.dataset.misc_info" class="job-error-text">
            <span>{{ props.dataset.misc_info }}</span>
        </div>
    </div>
</template>
