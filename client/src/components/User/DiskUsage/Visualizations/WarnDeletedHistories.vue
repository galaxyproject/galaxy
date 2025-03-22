<template>
    <p class="text-justify">
        注意：这些图表包含<b>已删除的历史记录</b>。请记住，即使您删除了历史记录，它们仍然占用存储空间。但是，您可以通过在
        <router-link :to="{ name: 'StorageManager' }"><b>存储管理器</b></router-link>页面的
        <i>废弃项目</i>部分永久删除它们，或者在图表中单独选择它们并点击<b>永久删除</b>按钮来释放存储空间。
    </p>
</template>
