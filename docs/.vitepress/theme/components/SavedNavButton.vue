<script setup lang="ts">
// 导航栏右侧“收藏”按钮（在简繁切换按钮左边），带收藏篇数的小圆点
import { onMounted } from 'vue'
import { withBase, useRoute } from 'vitepress'
import { passages, loadPassages, watchScript, T } from '../saved'
const route = useRoute()
onMounted(() => { watchScript(); loadPassages() })
</script>

<template>
  <a class="dt-navsave" :class="{ on: route.path.startsWith(withBase('/saved')) }" :href="withBase('/saved')" :title="T('我的收藏', '我的收藏')">
    <i class="dt-ico ico-bookmark" aria-hidden="true"></i>
    <span class="dt-navsave-txt">{{ T('收藏', '收藏') }}</span>
    <b v-if="passages.length" class="dt-badge">{{ passages.length > 99 ? '99+' : passages.length }}</b>
  </a>
</template>
