<template>
    <p class="text-justify">
        注意：这些图表包括<b>已删除的数据集</b>。请记住，即使您删除了数据集，它们仍然占用
        存储空间。但是，您可以通过从
        <i>废弃项目</i>部分
        <router-link :to="{ name: 'StorageManager' }"><b>存储管理器</b></router-link>页面永久删除它们来释放存储空间，或者通过在
        图表中单独选择它们并点击<b>永久删除</b>按钮来释放存储空间。
    </p>
</template>
