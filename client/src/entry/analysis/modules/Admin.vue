<template>
    <div id="columns" class="d-flex">
        <div id="center" class="overflow-auto p-3 w-100">
            <router-view :key="$route.fullPath" class="h-100" />
        </div>
    </div>
</template>
