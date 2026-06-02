<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' }
})

const el = ref(null)
let chart = null

function render() { if (chart) chart.setOption(props.option, true) }
function resize() { if (chart) chart.resize() }

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', resize)
})
watch(() => props.option, render, { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) chart.dispose()
})
</script>

<template>
  <div ref="el" :style="{ height }"></div>
</template>
