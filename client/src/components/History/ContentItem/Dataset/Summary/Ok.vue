<template functional>
    <div v-if="props.dataset">
        <div v-if="props.dataset.misc_blurb" class="blurb">
            <span class="value">{{ props.dataset.misc_blurb }}</span>
        </div>
        <div v-if="props.dataset.file_ext" class="datatype">
            <label class="prompt" v-localize>format</label>
            <span class="value">{{ props.dataset.file_ext }}</span>
        </div>
        <div v-if="props.dataset.genome_build" class="dbkey">
            <label class="prompt" v-localize>database</label>
            <b-link class="value" @click.stop="listeners['edit']()">{{ props.dataset.genome_build }}</b-link>
        </div>
        <div v-if="props.dataset.misc_info" class="info">
            <span class="value">{{ props.dataset.misc_info }}</span>
        </div>
    </div>
</template>
