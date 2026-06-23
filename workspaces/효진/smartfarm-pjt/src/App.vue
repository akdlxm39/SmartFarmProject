<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import GaugeChart from './components/GaugeChart.vue'

// Time formatting
const currentTime = ref('')
let timer = null

const updateTime = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const date = String(now.getDate()).padStart(2, '0')
  const days = ['일', '월', '화', '수', '목', '금', '토']
  const day = days[now.getDay()]
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  currentTime.value = `${year}년 ${month}월 ${date}일 (${day}) ${hours}:${minutes}`
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

// Sensor Data
const sensors = ref([
  { id: 'temp', label: '온도', value: 15, max: 30, unit: '°C', color: '#00b050', status: '정상', statusIcon: 'fa-regular fa-face-smile', statusColor: '#4caf50' },
  { id: 'humi', label: '습도', value: 60, max: 100, unit: '%', color: '#00b050', status: '정상', statusIcon: 'fa-regular fa-face-smile', statusColor: '#4caf50' },
  { id: 'water', label: '수온', value: 15, max: 30, unit: '°C', color: '#ffeb3b', status: '주의', statusIcon: 'fa-regular fa-face-meh', statusColor: '#ffc107' },
  { id: 'lux', label: '조도', value: 250, max: 300, unit: 'LUX', color: '#f44336', status: '위험', statusIcon: 'fa-regular fa-face-frown', statusColor: '#f44336' }
])

// Operation Mode
const isAutoMode = ref(true)

const controls = ref({
  water: true,
  window: true,
  power: false,
  ac: false
})

const deviceLights = ref([
  { label: '냉방기', active: true, color: '#2196f3' },
  { label: '난방기', active: false, color: '#ff5722' },
  { label: '가습기', active: false, color: '#9c27b0' },
  { label: '제습기', active: false, color: '#ffeb3b' },
  { label: '환풍기', active: true, color: '#8bc34a' }
])
</script>

<template>
  <div class="dashboard-wrapper">
    <!-- Header -->
    <header class="app-header">
      <h1 class="farm-title">무럭무럭 농장</h1>
      <div class="current-time">{{ currentTime }}</div>
    </header>

    <main class="dashboard-content">
      
      <!-- Sensor Section -->
      <section class="panel sensor-panel">
        <div class="sensor-grid">
          <div v-for="sensor in sensors" :key="sensor.id" class="sensor-item">
            <h3 class="sensor-label">{{ sensor.label }}</h3>
            <div class="gauge-wrapper">
              <GaugeChart 
                :value="sensor.value" 
                :max="sensor.max" 
                :unit="sensor.unit" 
                :color="sensor.color" 
              />
            </div>
            <div class="sensor-status" :style="{ color: sensor.statusColor }">
              <i :class="sensor.statusIcon" class="status-icon"></i>
              <span class="status-text">{{ sensor.status }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Operation Control Section -->
      <section class="panel control-panel">
        <div class="panel-header">
          <h2>운영모드</h2>
          <div class="mode-toggle">
            <span :class="{ active: isAutoMode }">자동</span>
            <label class="switch">
              <input type="checkbox" v-model="isAutoMode">
              <span class="slider round"></span>
            </label>
            <span :class="{ active: !isAutoMode }">수동</span>
          </div>
        </div>
        
        <div class="control-body">
          <div class="control-left">
            <!-- 급수 -->
            <div class="control-item">
              <div class="control-icon-wrapper">
                <i class="fa-solid fa-seedling control-icon"></i>
                <span>급수</span>
              </div>
              <div class="btn-group">
                <button :class="['btn btn-on', { active: controls.water }]" @click="controls.water = true">ON</button>
                <button :class="['btn btn-off', { active: !controls.water }]" @click="controls.water = false">OFF</button>
              </div>
            </div>
            <!-- 창문 -->
            <div class="control-item">
              <div class="control-icon-wrapper">
                <i class="fa-solid fa-person-shelter control-icon"></i>
                <span>창문</span>
              </div>
              <div class="btn-group">
                <button :class="['btn btn-on', { active: controls.window }]" @click="controls.window = true">열기</button>
                <button :class="['btn btn-off', { active: !controls.window }]" @click="controls.window = false">닫기</button>
              </div>
            </div>
            <!-- 전원 -->
            <div class="control-item">
              <div class="control-icon-wrapper">
                <i class="fa-solid fa-power-off control-icon"></i>
                <span>전원</span>
              </div>
              <div class="btn-group">
                <button :class="['btn btn-on', { active: controls.power }]" @click="controls.power = true">ON</button>
                <button :class="['btn btn-off', { active: !controls.power }]" @click="controls.power = false">OFF</button>
              </div>
            </div>
            <!-- 냉난방 -->
            <div class="control-item">
              <div class="control-icon-wrapper">
                <i class="fa-solid fa-temperature-half control-icon"></i>
                <span>냉난방</span>
              </div>
              <div class="btn-group">
                <button :class="['btn btn-on', { active: controls.ac }]" @click="controls.ac = true">ON</button>
                <button :class="['btn btn-off', { active: !controls.ac }]" @click="controls.ac = false">OFF</button>
              </div>
            </div>
          </div>
          
          <div class="control-divider"></div>
          
          <div class="control-right">
            <div class="device-lights">
              <div v-for="(device, index) in deviceLights" :key="index" class="light-item">
                <div class="light-circle" :style="{ backgroundColor: device.active ? device.color : '#e0e0e0' }"></div>
                <span class="light-label">{{ device.label }}</span>
              </div>
            </div>
            <div class="warning-banner">
              <i class="fa-solid fa-triangle-exclamation"></i>
              <span>수온 및 조도 기준 초과!!</span>
            </div>
          </div>
        </div>
      </section>

      <!-- CCTV Section -->
      <section class="panel cctv-panel">
        <div class="panel-header cctv-header">
          <h2>농장 내부 / 트럭 CCTV</h2>
        </div>
        <div class="cctv-body">
          <div class="cctv-container">
            <div class="cctv-placeholder">
              <div class="cctv-label">INDOOR</div>
              <i class="fa-solid fa-video placeholder-icon"></i>
              <span>CCTV 화면 준비중</span>
            </div>
          </div>
          <div class="cctv-container">
            <div class="cctv-placeholder">
              <div class="cctv-label">TRUCK</div>
              <i class="fa-solid fa-video placeholder-icon"></i>
              <span>CCTV 화면 준비중</span>
            </div>
          </div>
        </div>
      </section>
      
    </main>
  </div>
</template>

<style>
/* Reset and Global Styles */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  background-color: #f5f7f9;
  color: #333;
}
</style>

<style scoped>
.dashboard-wrapper {
  max-width: 1000px;
  margin: 0 auto;
  background-color: white;
  min-height: 100vh;
  box-shadow: 0 0 20px rgba(0,0,0,0.1);
  padding-bottom: 30px;
}

/* Header */
.app-header {
  background-color: #00a83e;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
}
.farm-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
}
.current-time {
  font-size: 1.1rem;
  font-weight: 500;
}

/* Common Panel */
.dashboard-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.panel {
  border: 2px solid #2e7d32;
  border-radius: 8px;
  background-color: white;
  overflow: hidden;
}
.panel-header {
  background-color: #757575;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 20px;
  position: relative;
}
.panel-header h2 {
  font-size: 1.2rem;
  margin: 0;
}
.cctv-header {
  justify-content: center;
}

/* Sensor Panel */
.sensor-panel {
  padding: 20px;
}
.sensor-grid {
  display: flex;
  justify-content: space-around;
  align-items: center;
}
.sensor-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 25%;
}
.sensor-label {
  font-size: 1.1rem;
  color: #444;
  margin-bottom: 20px;
}
.gauge-wrapper {
  margin-bottom: 35px;
}
.sensor-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}
.status-icon {
  font-size: 3rem;
}
.status-text {
  font-size: 1.2rem;
  font-weight: bold;
}

/* Control Panel */
.mode-toggle {
  position: absolute;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: bold;
}
.mode-toggle span {
  opacity: 0.5;
}
.mode-toggle span.active {
  opacity: 1;
}
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}
.switch input { 
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc;
  transition: .4s;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
}
input:checked + .slider {
  background-color: #4caf50;
}
input:checked + .slider:before {
  transform: translateX(26px);
}
.slider.round {
  border-radius: 24px;
}
.slider.round:before {
  border-radius: 50%;
}

.control-body {
  display: flex;
  padding: 20px;
}
.control-left {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-gap: 20px;
}
.control-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.control-icon-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #555;
  font-weight: bold;
}
.control-icon {
  font-size: 2rem;
  margin-bottom: 5px;
}
.btn-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 80px;
}
.btn {
  border: none;
  border-radius: 4px;
  padding: 6px 0;
  font-weight: bold;
  cursor: pointer;
  color: white;
  transition: background-color 0.2s;
}
.btn-on {
  background-color: #e0e0e0;
  color: #666;
}
.btn-off {
  background-color: #e0e0e0;
  color: #666;
}
.btn-on.active {
  background-color: #00b050;
  color: white;
}
.btn-off.active {
  background-color: #757575;
  color: white;
}

.control-divider {
  width: 2px;
  background-color: #ccc;
  margin: 0 20px;
}

.control-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 20px;
}
.device-lights {
  display: flex;
  justify-content: space-between;
}
.light-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.light-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  box-shadow: inset 0 -3px 5px rgba(0,0,0,0.2);
}
.light-label {
  font-size: 0.9rem;
  font-weight: bold;
  color: #444;
}
.warning-banner {
  background-color: #ff9800;
  color: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  font-size: 1.5rem;
  font-weight: bold;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* CCTV Panel */
.cctv-body {
  display: flex;
  background-color: #000;
  padding: 5px;
  gap: 5px;
}
.cctv-container {
  flex: 1;
  aspect-ratio: 4/3;
  background-color: #1a1a1a;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid #333;
}
.cctv-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #666;
  gap: 10px;
}
.placeholder-icon {
  font-size: 3rem;
}
.cctv-label {
  position: absolute;
  top: 10px;
  left: 10px;
  color: white;
  font-weight: bold;
  font-size: 1rem;
  background-color: rgba(0,0,0,0.5);
  padding: 2px 8px;
  border-radius: 4px;
}
</style>
