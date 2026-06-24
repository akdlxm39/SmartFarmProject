<template>
  <div class="gauge-container">
    <Doughnut :data="chartData" :options="chartOptions" />
    <div class="gauge-value">
      <strong>{{ value }}</strong
      ><span class="unit" v-if="unit">{{ unit }}</span>
    </div>
    <div class="gauge-minmax">
      <span>0</span>
      <span>{{ max }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Doughnut } from "vue-chartjs";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps({
  value: { type: Number, required: true },
  max: { type: Number, required: true },
  unit: { type: String, default: "" },
  color: { type: String, default: "#4caf50" },
});

const chartData = computed(() => {
  // Ensure value doesn't exceed max for visualization
  const displayValue = Math.min(props.value, props.max);
  return {
    labels: ["Value", "Empty"],
    datasets: [
      {
        data: [displayValue, props.max - displayValue],
        backgroundColor: [props.color, "#e0e0e0"],
        borderWidth: 0,
        cutout: "75%",
        borderRadius: [0, 0], // No rounded edges for a flat look if preferred
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  rotation: -90,
  circumference: 180,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
  layout: {
    padding: 0,
  },
};
</script>

<style scoped>
.gauge-container {
  position: relative;
  width: 180px;
  height: 90px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.gauge-value {
  position: absolute;
  bottom: 0px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}
.gauge-value strong {
  font-size: 1.5rem;
  color: #111;
  font-weight: bold;
}
.unit {
  font-size: 0.9rem;
  color: #333;
  margin-left: 2px;
}
.gauge-minmax {
  position: absolute;
  bottom: -20px;
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0 10px;
  font-size: 0.8rem;
  color: #666;
  box-sizing: border-box;
}
</style>
