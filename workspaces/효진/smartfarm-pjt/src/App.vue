<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import CropStatChart from "./components/CropStatChart.vue";
import CropTrendChart from "./components/CropTrendChart.vue";

// Trend Modal State
const showTrendModal = ref(false);
const trendLabels = ref(["월", "화", "수", "목", "금", "토", "오늘"]);
const trendHarvests = ref([1100, 1150, 1080, 1200, 1180, 1250, 1284]);
const trendDefectRates = ref([4.2, 3.8, 4.0, 3.5, 3.2, 2.8, 3.2]);

const openTrendModal = () => {
  showTrendModal.value = true;
};

const closeTrendModal = () => {
  showTrendModal.value = false;
};

// Time formatting
const currentTime = ref("");
let timer = null;

const updateTime = () => {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  currentTime.value = `${hours}:${minutes}:${seconds}`;
};

// Crop Data
const crops = ref([
  { id: "tomato", label: "토마토", good: 0, defect: 0, color: "#f44336" },
  { id: "carrot", label: "당근", good: 0, defect: 0, color: "#ff9800" },
  { id: "radish", label: "무", good: 0, defect: 0, color: "#8bc34a" },
]);

// Computed Stats
const totalHarvest = computed(() => crops.value.reduce((acc, c) => acc + c.good + c.defect, 0));
const totalDefects = computed(() => crops.value.reduce((acc, c) => acc + c.defect, 0));
const defectRate = computed(() =>
  totalHarvest.value === 0 ? 0 : ((totalDefects.value / totalHarvest.value) * 100).toFixed(1),
);
const turtlebotDeliveries = ref(42);

// Device Status
const deviceStatus = ref([
  {
    id: "dobot",
    name: "Dobot Magician",
    type: "로봇 암 (수확/분류)",
    status: "운영중",
    lastUpdate: "방금 전",
    icon: "fa-solid fa-robot",
  },
  {
    id: "camera",
    name: "Edge AI Camera",
    type: "라즈베리파이 (비전 판별)",
    status: "운영중",
    lastUpdate: "방금 전",
    icon: "fa-solid fa-camera",
  },
  {
    id: "conveyor",
    name: "컨베이어 벨트",
    type: "RGB-D 센서 연동",
    status: "대기중",
    lastUpdate: "2분 전",
    icon: "fa-solid fa-bars-progress",
  },
  {
    id: "turtlebot",
    name: "TurtleBot 3",
    type: "ROS2 자율주행 배송",
    status: "대기중",
    lastUpdate: "5분 전",
    icon: "fa-solid fa-truck-fast",
  },
]);

// System Logs
const logs = ref([]);

const addLog = (type, message) => {
  const now = new Date();
  const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  logs.value.unshift({ id: Date.now(), time: timeStr, type, message });
  if (logs.value.length > 10) logs.value.pop();
};

// Robot Controls
const manualControls = ref({
  eStop: false,
});

const toggleEStop = () => {
  manualControls.value.eStop = !manualControls.value.eStop;
  deviceStatus.value.forEach((d) => {
    if (manualControls.value.eStop) {
      d.status = "오류";
    } else {
      d.status = d.id === "conveyor" || d.id === "turtlebot" ? "대기중" : "운영중";
    }
  });

  if (manualControls.value.eStop) {
    addLog("error", "[시스템] 사용자에 의해 전체 시스템 긴급 정지(E-STOP) 발동");
  } else {
    addLog("success", "[시스템] 긴급 정지 해제, 자동화 프로세스 재가동");
  }
};

// WebSocket State
let ws = null;
let wsVision = null;
const conveyorVisionImage = ref(null);
const conveyorDetections = ref([]);

const initWebSocket = () => {
  ws = new WebSocket("ws://localhost:8000/ws");

  ws.onopen = () => {
    addLog("success", "[시스템] 백엔드 모드버스 서버 연동 완료");
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "conveyor_status") {
      const conveyor = deviceStatus.value.find((d) => d.id === "conveyor");
      if (conveyor && !manualControls.value.eStop) {
        if (conveyor.status !== message.data.status) {
          conveyor.status = message.data.status;
          addLog(
            conveyor.status === "운영중" ? "info" : "warning",
            `[시스템] 컨베이어 벨트 ${conveyor.status === "운영중" ? "가동" : "정지"}`,
          );
        }
        conveyor.lastUpdate = message.data.timestamp;
      }
      
      if (message.data.crop_counts) {
        const counts = message.data.crop_counts;
        const tomato = crops.value.find(c => c.id === "tomato");
        if (tomato && counts.tomato) {
          tomato.good = counts.tomato.good;
          tomato.defect = counts.tomato.bad;
        }
        const radish = crops.value.find(c => c.id === "radish");
        if (radish && counts.radish) {
          radish.good = counts.radish.good;
          radish.defect = counts.radish.bad;
        }
      }
    } else if (message.type === "control_result") {
      if (message.data.success) {
        addLog(
          "info",
          `[모드버스] 컨베이어 벨트 ${message.data.action === "start" ? "가동" : "정지"} 명령 성공`,
        );
      } else {
        addLog("error", `[모드버스] 컨베이어 제어 명령 실패`);
      }
    }
  };

  ws.onclose = () => {
    // 연결 끊김 알림 (도배 방지를 위해 생략 가능하나 디버깅을 위해 추가)
    // addLog('warning', '[시스템] 서버 접속 끊김. 5초 후 재접속...')
    setTimeout(initWebSocket, 5000);
  };
};

const initVisionWebSocket = () => {
  wsVision = new WebSocket("ws://192.168.110.109:28765");

  wsVision.onopen = () => {
    addLog("success", "[시스템] 비전 시스템 연동 완료");
  };

  let isFirstFrameReceived = false;
  let previousVisionEvent = 0; // 0 = EVENT_NONE

  wsVision.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "conveyor_roi_result") {
      if (!isFirstFrameReceived) {
        isFirstFrameReceived = true;
        addLog("success", "[시스템] 비전 영상 데이터 수신 시작");
      }
      if (message.image_jpeg_base64) {
        conveyorVisionImage.value = `data:image/jpeg;base64,${message.image_jpeg_base64}`;
      }
      conveyorDetections.value = message.detections;

      // 카메라 화면에 잠깐 스칠 때가 아니라, 컨베이어 벨트에 안정적으로 놓여졌을 때(EVENT_CUBE_DETECTED) 로깅
      if (message.modbus_state) {
        const currentEvent = message.modbus_state.last_vision_event;
        const color = message.modbus_state.cube_color;

        // 1 = EVENT_CUBE_DETECTED (물체가 놓여짐 상태로 새로 진입했을 때만 1회 트리거)
        if (currentEvent === 1 && previousVisionEvent !== 1) {
          if (color === 1) { // 1 = COLOR_RED
            addLog("success", "AI 비전: 토마토 인식");
          } else if (color === 2) { // 2 = COLOR_GREEN
            addLog("success", "AI 비전: 무 인식");
          }
        }
        previousVisionEvent = currentEvent;
      }
    }
  };

  wsVision.onerror = (error) => {
    console.error("Vision WebSocket Error:", error);
  };

  wsVision.onclose = () => {
    addLog("warning", "[시스템] 비전 시스템 연결 끊김. 5초 후 재접속...");
    setTimeout(initVisionWebSocket, 5000);
  };
};

// Data Mocking
onMounted(() => {
  initWebSocket();
  initVisionWebSocket();
  updateTime();
  timer = setInterval(updateTime, 1000);
});

onUnmounted(() => {
  clearInterval(timer);
  if (ws) ws.close();
  if (wsVision) wsVision.close();
});

// CCTV Modal
const activeCctv = ref(null);
const cctvZoom = ref(1);

const openCctv = (label) => {
  activeCctv.value = label;
  cctvZoom.value = 1;
};

const closeCctv = () => {
  activeCctv.value = null;
};

const zoomIn = () => {
  if (cctvZoom.value < 3) cctvZoom.value += 0.2;
};

const zoomOut = () => {
  if (cctvZoom.value > 0.5) cctvZoom.value -= 0.2;
};

const handleWheel = (event) => {
  if (event.deltaY < 0) {
    zoomIn();
  } else {
    zoomOut();
  }
};
</script>

<template>
  <div class="sf-container">
    <!-- Header -->
    <header class="sf-header">
      <div>
        <h1 class="sf-title">Smart Farm 관제 시스템</h1>
        <p class="sf-subtitle">로봇 통합 물류 자동화 대시보드</p>
      </div>
      <div class="sf-header-actions">
        <div class="sf-status-badge">
          <span class="sf-status-dot"></span>
          System Online
        </div>
        <div class="sf-time-badge">
          <i class="fa-regular fa-clock" style="margin-right: 4px"></i> {{ currentTime }}
        </div>
        <button class="sf-icon-btn"><i class="fa-solid fa-gear"></i></button>
      </div>
    </header>

    <!-- Main Grid Layout -->
    <div class="sf-main-grid">
      <!-- Left Column (Stats & Charts) -->
      <div class="sf-left-col">
        <!-- Top Stats Row -->
        <div class="sf-stats-row">
          <div class="sf-stat-card">
            <div class="sf-stat-header">
              <div class="sf-stat-icon-wrapper text-emerald-500">
                <i class="fa-solid fa-box"></i>
              </div>
              <span class="sf-stat-trend trend-up"
                ><i class="fa-solid fa-arrow-trend-up"></i> 12%</span
              >
            </div>
            <h3 class="sf-stat-title">오늘의 총 수확량</h3>
            <div class="sf-stat-value-group">
              <span class="sf-stat-value">{{ totalHarvest }}</span>
              <span class="sf-stat-unit">개</span>
            </div>
          </div>

          <div class="sf-stat-card">
            <div class="sf-stat-header">
              <div class="sf-stat-icon-wrapper text-rose-500">
                <i class="fa-solid fa-circle-exclamation"></i>
              </div>
              <span class="sf-stat-trend trend-down"
                ><i class="fa-solid fa-arrow-trend-down"></i> 0.8%</span
              >
            </div>
            <h3 class="sf-stat-title">AI 불량 검출률</h3>
            <div class="sf-stat-value-group">
              <span class="sf-stat-value">{{ defectRate }}</span>
              <span class="sf-stat-unit">%</span>
            </div>
          </div>

          <div class="sf-stat-card">
            <div class="sf-stat-header">
              <div class="sf-stat-icon-wrapper text-indigo-500">
                <i class="fa-solid fa-truck"></i>
              </div>
              <span class="sf-stat-trend trend-up"
                ><i class="fa-solid fa-arrow-trend-up"></i> 5%</span
              >
            </div>
            <h3 class="sf-stat-title">터틀봇 누적 배송</h3>
            <div class="sf-stat-value-group">
              <span class="sf-stat-value">{{ turtlebotDeliveries }}</span>
              <span class="sf-stat-unit">회</span>
            </div>
          </div>
        </div>

        <!-- Crop Stats -->
        <div class="sf-panel">
          <div class="sf-panel-header-simple">
            <h2 class="sf-panel-title">
              <i class="fa-solid fa-chart-pie text-slate-400"></i> 작물 수확 및 품질 통계
            </h2>
            <button class="sf-text-btn" @click="openTrendModal">
              상세보기 <i class="fa-solid fa-chevron-right"></i>
            </button>
          </div>
          <div class="crop-stats-body mt-4">
            <CropStatChart
              v-for="crop in crops"
              :key="crop.id"
              :label="crop.label"
              :good="crop.good"
              :defect="crop.defect"
              :color="crop.color"
            />
          </div>
        </div>

        <!-- CCTV -->
        <div class="sf-panel flex-1">
          <div class="sf-panel-header-simple mb-4">
            <h2 class="sf-panel-title">
              <i class="fa-solid fa-video text-slate-400"></i> 실시간 CCTV 모니터링
            </h2>
          </div>
          <div class="cctv-body">
            <div class="cctv-container" @click="openCctv('CONVEYOR VISION')">
              <img v-if="conveyorVisionImage" :src="conveyorVisionImage" class="cctv-image" />
              <div v-else class="cctv-placeholder">
                <div class="cctv-label">CONVEYOR VISION</div>
                <i class="fa-solid fa-camera placeholder-icon"></i>
                <span>CCTV 화면 준비중</span>
              </div>
              <div v-if="conveyorVisionImage" class="cctv-label">CONVEYOR VISION</div>
            </div>
            <div class="cctv-container" @click="openCctv('TURTLEBOT DELIVERY')">
              <div class="cctv-placeholder">
                <div class="cctv-label">TURTLEBOT DELIVERY</div>
                <i class="fa-solid fa-camera placeholder-icon"></i>
                <span>CCTV 화면 준비중</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column (Devices & Logs) -->
      <div class="sf-right-col">
        <!-- Device Status -->
        <div class="sf-device-list">
          <h2 class="sf-section-label">연동 기기 상태</h2>
          <div v-for="device in deviceStatus" :key="device.id" class="sf-device-card">
            <div class="sf-device-info">
              <div
                class="sf-device-icon"
                :class="`status-${device.status === '운영중' ? 'active' : device.status === '대기중' ? 'idle' : 'error'}`"
              >
                <i :class="device.icon"></i>
              </div>
              <div>
                <h4 class="sf-device-name">{{ device.name }}</h4>
                <p class="sf-device-type">{{ device.type }}</p>
              </div>
            </div>
            <div class="sf-device-meta">
              <div class="sf-device-status-badge">
                <span class="sf-device-status-text">{{ device.status }}</span>
                <span
                  class="sf-status-dot-small"
                  :class="`bg-${device.status === '운영중' ? 'emerald' : device.status === '대기중' ? 'amber' : 'rose'}`"
                ></span>
              </div>
              <span class="sf-device-time"
                ><i class="fa-regular fa-clock"></i> {{ device.lastUpdate }}</span
              >
            </div>
          </div>
        </div>

        <!-- Robot Controls -->
        <div class="sf-robot-controls">
          <button
            class="sf-btn-estop"
            :class="{ 'estop-active': manualControls.eStop }"
            @click="toggleEStop"
          >
            <img src="/siren.png" alt="Siren" class="siren-icon" />
            <span>{{ manualControls.eStop ? "긴급 정지 해제" : "전체 시스템 STOP" }}</span>
          </button>
        </div>

        <!-- System Logs -->
        <div class="sf-panel sf-log-panel flex-1">
          <div class="sf-panel-header-bg">
            <h2 class="sf-panel-title">
              <i class="fa-solid fa-list-ul text-slate-500"></i> 실시간 시스템 로그
            </h2>
          </div>
          <div class="sf-log-body">
            <div v-for="log in logs" :key="log.id" class="sf-log-item">
              <div class="sf-log-time">{{ log.time }}</div>
              <div class="sf-log-dot" :class="`bg-${log.type}`"></div>
              <p class="sf-log-msg" :class="`text-${log.type}`">{{ log.message }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- CCTV Modal overlay -->
    <div v-if="activeCctv" class="cctv-modal-overlay" @click.self="closeCctv">
      <div class="cctv-modal-content">
        <div class="cctv-modal-header">
          <h2>{{ activeCctv }}</h2>
          <button class="btn-close" @click="closeCctv"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="cctv-modal-body" @wheel.prevent="handleWheel">
          <div class="cctv-zoom-wrapper" :style="{ transform: `scale(${cctvZoom})` }">
            <img
              v-if="activeCctv === 'CONVEYOR VISION' && conveyorVisionImage"
              :src="conveyorVisionImage"
              class="modal-image"
            />
            <template v-else>
              <i class="fa-solid fa-video modal-video-icon"></i>
              <span>CCTV 화면 준비중</span>
            </template>
          </div>
        </div>
        <div class="cctv-modal-controls">
          <button class="btn-zoom" @click="zoomOut"><i class="fa-solid fa-minus"></i> 축소</button>
          <span class="zoom-level">{{ Math.round(cctvZoom * 100) }}%</span>
          <button class="btn-zoom" @click="zoomIn"><i class="fa-solid fa-plus"></i> 확대</button>
        </div>
      </div>
    </div>

    <!-- Trend Modal overlay -->
    <div v-if="showTrendModal" class="cctv-modal-overlay" @click.self="closeTrendModal">
      <div class="trend-modal-content">
        <div class="cctv-modal-header">
          <h2>주간 작물 수확 트렌드 분석</h2>
          <button class="btn-close" @click="closeTrendModal">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="trend-modal-body">
          <CropTrendChart
            :labels="trendLabels"
            :harvests="trendHarvests"
            :defectRates="trendDefectRates"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');

/* Globals & Variables */
:root {
  --slate-50: #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-400: #94a3b8;
  --slate-500: #64748b;
  --slate-600: #475569;
  --slate-800: #1e293b;

  --emerald-50: #ecfdf5;
  --emerald-100: #d1fae5;
  --emerald-500: #10b981;
  --emerald-600: #059669;

  --amber-50: #fffbeb;
  --amber-100: #fef3c7;
  --amber-400: #fbbf24;
  --amber-500: #f59e0b;
  --amber-600: #d97706;

  --rose-50: #fff1f2;
  --rose-100: #ffe4e6;
  --rose-500: #f43f5e;
  --rose-600: #e11d48;

  --blue-50: #eff6ff;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;

  --indigo-500: #6366f1;
  --indigo-600: #4f46e5;
}

body {
  font-family: 'Jua', sans-serif;
  font-size: 17px;
  font-weight: 400; /* 배민 주아체 기본 굵기로 초기화 (브라우저의 가짜 볼드 방지) */
  -webkit-font-smoothing: antialiased; /* 글씨 렌더링을 부드럽게 하여 약간 얇아 보이게 함 */
  background-color: var(--slate-50);
  color: var(--slate-800);
  margin: 0;
  padding: 0;
}
</style>

<style scoped>
.sf-container {
  min-height: 100vh;
  padding: 24px;
  box-sizing: border-box;
  max-width: 1600px;
  margin: 0 auto;
}

/* Header */
.sf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}
.sf-title {
  font-size: 1.5rem;
  font-weight: 400;
  margin: 0;
  letter-spacing: -0.025em;
  color: var(--slate-800);
}
.sf-subtitle {
  font-size: 0.875rem;
  color: var(--slate-500);
  margin: 4px 0 0 0;
}
.sf-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sf-status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 400;
  padding: 6px 12px;
  background-color: var(--emerald-50);
  color: var(--emerald-600);
  border-radius: 8px;
}
.sf-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--emerald-500);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.sf-time-badge {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--slate-600);
  padding: 6px 12px;
  background-color: white;
  border-radius: 8px;
  border: 1px solid var(--slate-200);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}
.sf-icon-btn {
  padding: 8px 12px;
  color: var(--slate-400);
  background-color: white;
  border-radius: 8px;
  border: 1px solid var(--slate-200);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}
.sf-icon-btn:hover {
  color: var(--slate-600);
  border-color: var(--slate-400);
}

/* Grid Layout */
.sf-main-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}
@media (min-width: 1024px) {
  .sf-main-grid {
    grid-template-columns: repeat(12, 1fr);
  }
  .sf-left-col {
    grid-column: span 8;
  }
  .sf-right-col {
    grid-column: span 4;
  }
}
.sf-left-col,
.sf-right-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.flex-1 {
  flex: 1;
}
.mb-4 {
  margin-bottom: 16px;
}

/* Stat Cards */
.sf-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.sf-stat-card {
  background-color: white;
  padding: 24px;
  border-radius: 16px;
  border: 1px solid var(--slate-100);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}
.sf-stat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.sf-stat-icon-wrapper {
  padding: 8px 10px;
  background-color: var(--slate-50);
  border-radius: 8px;
  font-size: 1.25rem;
}
.text-emerald-500 {
  color: var(--emerald-500);
}
.text-rose-500 {
  color: var(--rose-500);
}
.text-indigo-500 {
  color: var(--indigo-500);
}

.sf-stat-trend {
  font-size: 0.75rem;
  font-weight: 400;
  padding: 4px 8px;
  border-radius: 9999px;
}
.trend-up {
  color: var(--emerald-500);
  background-color: var(--emerald-50);
}
.trend-down {
  color: var(--rose-500);
  background-color: var(--rose-50);
}

.sf-stat-title {
  color: var(--slate-500);
  font-size: 0.875rem;
  font-weight: 400;
  margin: 0 0 4px 0;
}
.sf-stat-value-group {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.sf-stat-value {
  font-size: 1.75rem;
  font-weight: 400;
  color: var(--slate-800);
}
.sf-stat-unit {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--slate-400);
}

/* Generic Panel */
.sf-panel {
  background-color: white;
  padding: 24px;
  border-radius: 16px;
  border: 1px solid var(--slate-100);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}
.sf-panel-header-simple {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sf-panel-title {
  font-size: 1.125rem;
  font-weight: 400;
  color: var(--slate-800);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
.text-slate-400 {
  color: var(--slate-400);
}
.text-slate-500 {
  color: var(--slate-500);
}
.sf-text-btn {
  background: none;
  border: none;
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--indigo-600);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}
.mt-4 {
  margin-top: 16px;
}

/* Crop Stats inside Panel */
.crop-stats-body {
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

/* Device List */
.sf-device-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sf-section-label {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--slate-500);
  margin: 0 0 4px 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.sf-device-card {
  background-color: white;
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--slate-100);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: border-color 0.2s;
}
.sf-device-card:hover {
  border-color: var(--slate-200);
}
.sf-device-info {
  display: flex;
  align-items: center;
  gap: 16px;
}
.sf-device-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  font-size: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid transparent;
}
.status-active {
  color: var(--emerald-500);
  border-color: var(--emerald-100);
  background-color: var(--emerald-50);
}
.status-idle {
  color: var(--amber-500);
  border-color: var(--amber-100);
  background-color: var(--amber-50);
}
.status-error {
  color: var(--rose-500);
  border-color: var(--rose-100);
  background-color: var(--rose-50);
}

.sf-device-name {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--slate-800);
  margin: 0 0 4px 0;
}
.sf-device-type {
  font-size: 0.75rem;
  color: var(--slate-400);
  margin: 0;
}
.sf-device-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
.sf-device-status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sf-device-status-text {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--slate-500);
}
.sf-status-dot-small {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.bg-emerald {
  background-color: var(--emerald-500);
  animation: pulse 2s infinite;
}
.bg-amber {
  background-color: var(--amber-400);
}
.bg-rose {
  background-color: var(--rose-500);
}

.sf-device-time {
  font-size: 0.625rem;
  color: var(--slate-400);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Robot Controls */
.sf-robot-controls {
  display: flex;
  gap: 16px;
}
.sf-btn-estop {
  flex: 1;
  background-color: #ca2424;
  color: white;
  border: none;
  padding: 16px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: 0 4px 6px -1px rgba(153, 27, 27, 0.3);
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.siren-icon {
  width: 48px;
  height: 48px;
  object-fit: contain;
}
.sf-btn-estop.estop-active .siren-icon {
  animation: ring-siren 0.5s ease-in-out infinite;
}
@keyframes ring-siren {
  0% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-15deg);
  }
  50% {
    transform: rotate(0deg);
  }
  75% {
    transform: rotate(15deg);
  }
  100% {
    transform: rotate(0deg);
  }
}
.sf-btn-estop:hover {
  background-color: #7f1d1d;
}
.sf-btn-estop.estop-active {
  background-color: var(--amber-500);
  box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.3);
  animation: pulse-border 1.5s infinite;
}
@keyframes pulse-border {
  0% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(245, 158, 11, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
}
.sf-btn-outline {
  flex: 1;
  background-color: white;
  color: var(--slate-600);
  border: 1px solid var(--slate-200);
  padding: 16px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}
.sf-btn-outline:hover:not(:disabled) {
  background-color: var(--slate-50);
}
.sf-btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* System Logs */
.sf-log-panel {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.sf-panel-header-bg {
  padding: 20px 24px;
  background-color: rgba(248, 250, 252, 0.5); /* slate-50/50 */
  border-bottom: 1px solid var(--slate-100);
}
.sf-log-body {
  padding: 0 24px;
  overflow-y: auto;
  flex: 1;
  max-height: 250px;
}
.sf-log-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px 0;
  border-bottom: 1px solid var(--slate-50);
}
.sf-log-item:last-child {
  border-bottom: none;
}
.sf-log-time {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--slate-400);
  padding-top: 2px;
  white-space: nowrap;
}
.sf-log-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.sf-log-msg {
  font-size: 0.875rem;
  margin: 0;
  line-height: 1.5;
  color: var(--slate-600);
}

/* Log Type Colors */
.bg-success {
  background-color: var(--emerald-500);
}
.text-success {
  color: var(--emerald-600);
}
.bg-info {
  background-color: var(--blue-500);
}
.text-info {
  color: var(--blue-600);
}
.bg-warning {
  background-color: var(--amber-500);
}
.text-warning {
  color: var(--amber-600);
}
.bg-error {
  background-color: var(--rose-500);
}
.text-error {
  color: var(--rose-600);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* CCTV Panel */
.cctv-body {
  display: flex;
  gap: 16px;
  height: 100%;
}
.cctv-container {
  flex: 1;
  aspect-ratio: 4/3;
  background-color: var(--slate-800);
  border-radius: 12px;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid var(--slate-600);
  cursor: pointer;
  transition:
    opacity 0.2s,
    transform 0.2s;
  overflow: hidden;
  min-height: 250px;
}
.cctv-container:hover {
  opacity: 0.9;
  transform: scale(0.99);
}
.cctv-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--slate-400);
  gap: 12px;
}
.cctv-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: absolute;
  top: 0;
  left: 0;
}
.placeholder-icon {
  font-size: 3rem;
}
.cctv-label {
  position: absolute;
  top: 16px;
  left: 16px;
  color: white;
  font-weight: 400;
  font-size: 0.75rem;
  background-color: rgba(0, 0, 0, 0.6);
  padding: 6px 10px;
  border-radius: 8px;
  letter-spacing: 0.05em;
}

/* CCTV Modal */
.cctv-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(15, 23, 42, 0.85); /* slate-900 */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}
.cctv-modal-content {
  background-color: var(--slate-800);
  border: 1px solid var(--slate-600);
  border-radius: 16px;
  width: 90%;
  max-width: 1000px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}
.cctv-modal-header {
  background-color: #0f172a;
  color: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--slate-600);
}
.cctv-modal-header h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 400;
}
.btn-close {
  background: none;
  border: none;
  color: var(--slate-400);
  font-size: 1.5rem;
  cursor: pointer;
  transition: color 0.2s;
}
.btn-close:hover {
  color: var(--rose-500);
}
.cctv-modal-body {
  aspect-ratio: 16/9;
  background-color: #000;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: relative;
}
.cctv-zoom-wrapper {
  transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--slate-500);
  gap: 20px;
}
.modal-video-icon {
  font-size: 4rem;
}
.modal-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.cctv-modal-controls {
  background-color: #0f172a;
  padding: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  color: white;
  border-top: 1px solid var(--slate-600);
}
.btn-zoom {
  background-color: var(--slate-700);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 400;
  display: flex;
  gap: 8px;
  align-items: center;
  transition: background-color 0.2s;
}
.btn-zoom:hover {
  background-color: var(--slate-600);
}
.btn-zoom:active {
  transform: scale(0.95);
}
.zoom-level {
  font-weight: 400;
  min-width: 60px;
  text-align: center;
  font-size: 1rem;
}

/* Trend Modal */
.trend-modal-content {
  background-color: white;
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}
.trend-modal-body {
  padding: 24px;
}
</style>
