# 🌐 스마트팜 통합 시스템 통신 방식 정의서

## 1. 시스템 아키텍처 개요

본 스마트팜 시스템은 '노트북(Main Hub)'을 중앙 관제탑으로 삼아 모든 통신과 제어가 이루어지는 중앙 집중형(Centralized) 아키텍처입니다.
노트북 내부에는 크게 3가지 핵심 서버/엔진이 구동되며 서로 유기적으로 데이터를 교환합니다.

* **FastAPI (Backend):** 웹 클라이언트(Vue.js)와의 WebSocket 통신을 중계하고, 수집된 이미지를 바탕으로 양/불량 AI 추론을 수행합니다.
* **Modbus Server (Shared Memory):** 모든 하드웨어 장치(컨베이어, 터틀봇 등)의 상태값과 제어 명령이 기록되는 중앙 공유 레지스터 역할을 합니다.
* **ROS 2 Core:** 로봇(Dobot)의 정밀한 모션 제어 및 카메라(RealSense) 스트리밍 토픽을 처리합니다.

## 2. 하드웨어별 세부 동작 및 통신 프로토콜

### 📦 1. 컨베이어 벨트 동작 제어

컨베이어 벨트는 상황에 따라 3가지 방식으로 제어되며, 최종적으로는 모두 Modbus를 통해 동작합니다.

* **웹 대시보드(APP) 원격 제어:**
* `Vue.js APP` ➔ **(WebSocket)** ➔ `노트북 FastAPI` ➔ **(Write)** ➔ `노트북 Modbus Server` ➔ **(Read)** ➔ `컨베이어 Modbus` ➔ 모터 작동


* **RealSense 기반 자동 제어:**
* RealSense 카메라가  **(Topic 발행)** ➔ `노트북 ROS 2` ➔ **(Write)** ➔ `노트북 Modbus Server` ➔ **(Read)** ➔ `컨베이어 Modbus` ➔ 모터 작동


* **라즈베리파이 물리 버튼 제어:**
* 라즈베리파이 버튼 입력 시 물리적으로 컨베이어 벨트 모터 직접 제어 (ON/OFF)


* **상태 실시간 업데이트:**
* `노트북 FastAPI`가 `노트북 Modbus Server`의 레지스터를 주기적으로 **Read** ➔ **(WebSocket)** ➔ `Vue.js APP`에 상태 전송 및 화면 갱신



### 🚚 2. 자율주행 물류 로봇 (TurtleBot)

터틀봇은 제어/상태 데이터와 영상 데이터를 분리하여 전송합니다.

* **로봇 상태 동기화 (이동, 정지, 목적지 도착 등):**
* `터틀봇 Modbus` ➔ **(Write)** ➔ `노트북 Modbus Server` ➔ **(Read)** ➔ `FastAPI` ➔ **(WebSocket)** ➔ `Vue.js APP` 반영


* **1인칭 주행 영상(PI Camera) 스트리밍:**
* 터틀봇 ROS 내부에 이미지 토픽 ➔ WebSocket 변환 코드 구현 ➔ **(WebSocket)** ➔ `Vue.js APP`으로 실시간 영상 다이렉트 전송



### 🦾 3. 로봇 암 (Dobot Magician)

Dobot은 정밀한 좌표 제어를 위해 ROS 2를 사용하며, 상태값만 Modbus를 통해 웹으로 보고합니다.

* **로봇 모션 제어:**
* `노트북 ROS 2` 노드를 통해 Dobot의 기구학적 동작 및 툴 제어


* **작업 상태 웹 실시간 반영:**
* `Dobot Modbus` ➔ **(Write)** ➔ `노트북 Modbus Server` ➔ **(Read)** ➔ `FastAPI` ➔ **(WebSocket)** ➔ `Vue.js APP`에 현재 작업 상태 반영



### 👁️ 4. 비전 감시 및 검사 시스템

카메라의 종류와 목적에 따라 통신 파이프라인이 다르게 적용됩니다.

* **RealSense (컨베이어 전체 감시용):**
* RealSense 영상 ➔ **(Topic 발행)** ➔ `노트북 ROS 2` ➔ 내부 코드로 이미지 토픽을 WebSocket 변환 ➔ **(WebSocket)** ➔ `Vue.js APP`으로 스트리밍


* **PI Camera (수확물 양품/불량품 AI 검사용):**
1. Dobot이 수확한 작물을 PI 카메라 앞으로 이동
2. PI 카메라 사진 촬영 ➔ **(WebSocket)** ➔ `노트북 FastAPI`로 전송
3. `FastAPI` 내부에서 AI 모델로 양/불량 추론 (신뢰도 확보를 위해 이 과정을 총 3회 반복하여 판별)
4. 판별 결과에 따라 Dobot에 적재/폐기 명령 하달
5. 양/불량 누적 개수를 `노트북 Modbus Server`에 **Write**
6. `FastAPI`가 해당 레지스터를 **Read** ➔ **(WebSocket)** ➔ `Vue.js APP`의 수확량 통계 차트 업데이트



## 3. 핵심 프로토콜 요약

* **WebSocket (파란색 선):** 실시간 지연이 없어야 하는 '고용량 영상 스트리밍'과 웹 화면의 '실시간 UI 업데이트'에 사용됩니다.
* **Modbus TCP (초록색 선):** 각 장비의 '현재 상태값(단순 숫자/플래그)'과 '제어 트리거 명령'을 공유 레지스터에 기록하고 읽는 데 사용되어 결합도를 낮추고 안정성을 높입니다.
* **ROS 2 Topic (분홍색 선):** 로봇의 '정밀한 위치/모션 제어'와 초기 센서 **'로우 데이터(Raw Data)'** 처리에 사용됩니다.
