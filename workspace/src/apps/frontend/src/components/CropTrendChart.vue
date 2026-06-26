<script setup>
import { computed } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  LineController,
  BarController
} from 'chart.js'
import { Bar } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  LineController,
  BarController,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  labels: { type: Array, required: true },
  harvests: { type: Array, required: true },
  defectRates: { type: Array, required: true }
})

const chartData = computed(() => {
  return {
    labels: props.labels,
    datasets: [
      {
        type: 'line',
        label: '불량률 (%)',
        data: props.defectRates,
        borderColor: '#f43f5e',
        backgroundColor: '#f43f5e',
        borderWidth: 2,
        tension: 0.3,
        yAxisID: 'y1',
        order: 1
      },
      {
        type: 'bar',
        label: '총 수확량 (개)',
        data: props.harvests,
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderRadius: 4,
        yAxisID: 'y',
        order: 2
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      position: 'top',
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      titleFont: { size: 13 },
      bodyFont: { size: 12 },
      padding: 10,
      cornerRadius: 8,
    }
  },
  scales: {
    x: {
      grid: { display: false }
    },
    y: {
      type: 'linear',
      display: true,
      position: 'left',
      title: {
        display: true,
        text: '수확량 (개)',
        color: '#64748b'
      },
      grid: {
        color: '#f1f5f9'
      }
    },
    y1: {
      type: 'linear',
      display: true,
      position: 'right',
      title: {
        display: true,
        text: '불량률 (%)',
        color: '#64748b'
      },
      grid: {
        drawOnChartArea: false, // only want the grid lines for one axis to show up
      },
      min: 0,
    },
  }
}
</script>

<template>
  <div class="chart-container">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 350px;
  position: relative;
}
</style>
