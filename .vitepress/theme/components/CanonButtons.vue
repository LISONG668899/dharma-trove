<script setup lang="ts">
// 首页类目卡片下方：德格版《甘珠尔》《丹珠尔》两个按钮（藏文在上、中文在下）
import { withBase } from 'vitepress'
</script>

<template>
  <section class="dt-canon">
    <p class="dt-canon-head">
      <span class="dt-bo">སྡེ་དགེ་བཀའ་བསྟན།</span>
      <span class="dt-canon-zh">德格版藏文大藏经</span>
    </p>
    <div class="dt-canon-btns">
      <a class="dt-canon-btn" :href="withBase('/甘珠尔/')">
        <span class="dt-bo">བཀའ་འགྱུར།</span>
        <span class="dt-canon-zh">甘珠尔</span>
      </a>
      <a class="dt-canon-btn" :href="withBase('/丹珠尔/')">
        <span class="dt-bo">བསྟན་འགྱུར།</span>
        <span class="dt-canon-zh">丹珠尔</span>
      </a>
    </div>
  </section>
</template>
