<template>
    <p class="text-justify">
        Note: these graphs include <b>deleted datasets</b>. Remember that, even if you delete datasets, they still take
        up storage space. However, you can free up the storage space by permanently deleting them from the
        <i>Discarded Items</i> section of the
        <router-link :to="{ name: 'StorageManager' }"><b>Storage Manager</b></router-link> page or by selecting them
        individually in the graph and clicking the <b>Permanently Delete</b> button.
    </p>
</template>
