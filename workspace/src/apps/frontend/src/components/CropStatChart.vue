<template>
  <div class="crop-chart-container">
    <div class="chart-wrapper">
      <Doughnut :data="chartData" :options="chartOptions" />
      <div class="chart-center">
        <span class="crop-name" :style="{ color: color }">{{ label }}</span>
        <strong class="total-value">{{ total }}개</strong>
      </div>
    </div>
    <div class="stat-details">
      <div class="stat-item good">
        <span class="stat-label"><span class="dot"></span>양품</span>
        <strong>{{ good }}</strong>
      </div>
      <div class="stat-item defect">
        <span class="stat-label"><span class="dot defect-dot"></span>불량</span>
        <strong>{{ defect }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Doughnut } from "vue-chartjs";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps({
  label: { type: String, required: true },
  good: { type: Number, required: true },
  defect: { type: Number, required: true },
  color: { type: String, default: "#ff5722" }, // Crop's main color
});

const total = computed(() => props.good + props.defect);

const chartData = computed(() => {
  return {
    labels: ["양품", "불량품"],
    datasets: [
      {
        data: total.value === 0 ? [1, 0] : [props.good, props.defect],
        backgroundColor: total.value === 0 ? ["#e0e0e0", "#e0e0e0"] : [props.color, "#616161"],
        borderWidth: 0,
        cutout: "75%",
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
  layout: {
    padding: 0,
  },
};
</script>

<style scoped>
.crop-chart-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  background-color: #ffffff;
  border-radius: 12px;
  padding: 15px;
  box-shadow: inset 0 0 5px rgba(0,0,0,0.05);
  border: 1px solid #eee;
  flex: 1;
}
.chart-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
}
.chart-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.crop-name {
  font-size: 0.9rem;
  font-weight: bold;
}
.total-value {
  font-size: 1.2rem;
  color: #333;
}
.stat-details {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 100%;
}
.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  align-items: center;
  color: #555;
  margin: 0 10%;
}
.stat-label {
  display: flex;
  align-items: center;
  gap: 6px;
}
.stat-item strong {
  color: #111;
  font-weight: 700;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.good .dot {
  background-color: v-bind('props.color');
}
.defect-dot {
  background-color: #616161 !important;
}
</style>
