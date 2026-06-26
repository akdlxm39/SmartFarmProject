import React, { useState, useEffect } from 'react';
import { 
  Activity, Box, Truck, Cpu, AlertCircle, CheckCircle2, 
  Settings, Clock, ChevronRight, BarChart3, Camera
} from 'lucide-react';

// --- Components ---

// 1. 상태 요약 카드
const StatCard = ({ title, value, unit, icon: Icon, trend, trendValue }) => (
  <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col">
    <div className="flex justify-between items-start mb-4">
      <div className="p-2 bg-slate-50 text-slate-500 rounded-lg">
        <Icon size={20} />
      </div>
      {trend === 'up' && <span className="text-xs font-medium text-emerald-500 bg-emerald-50 px-2 py-1 rounded-full">+{trendValue}%</span>}
      {trend === 'down' && <span className="text-xs font-medium text-rose-500 bg-rose-50 px-2 py-1 rounded-full">-{trendValue}%</span>}
    </div>
    <h3 className="text-slate-500 text-sm font-medium mb-1">{title}</h3>
    <div className="flex items-baseline gap-1">
      <span className="text-2xl font-bold text-slate-800">{value}</span>
      <span className="text-sm font-medium text-slate-400">{unit}</span>
    </div>
  </div>
);

// 2. 기기 상태 카드 (포인트 컬러 적용)
const DeviceCard = ({ name, type, status, lastUpdate, icon: Icon }) => {
  const statusConfig = {
    '운영중': { color: 'text-emerald-500', bg: 'bg-emerald-500', border: 'border-emerald-100' },
    '대기중': { color: 'text-amber-500', bg: 'bg-amber-400', border: 'border-amber-100' },
    '오류': { color: 'text-rose-500', bg: 'bg-rose-500', border: 'border-rose-100' },
  };
  const currentStyle = statusConfig[status] || statusConfig['대기중'];

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between group hover:border-slate-200 transition-colors">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-xl bg-slate-50 ${currentStyle.color} border ${currentStyle.border}`}>
          <Icon size={24} />
        </div>
        <div>
          <h4 className="text-sm font-bold text-slate-800">{name}</h4>
          <p className="text-xs text-slate-400">{type}</p>
        </div>
      </div>
      <div className="flex flex-col items-end gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">{status}</span>
          <span className={`w-2.5 h-2.5 rounded-full ${currentStyle.bg} ${status === '운영중' ? 'animate-pulse' : ''}`}></span>
        </div>
        <span className="text-[10px] text-slate-400 flex items-center gap-1">
          <Clock size={10} /> {lastUpdate}
        </span>
      </div>
    </div>
  );
};

// 3. 로그 리스트 아이템
const LogItem = ({ time, type, message }) => {
  const typeStyles = {
    'info': 'text-blue-500 bg-blue-50',
    'success': 'text-emerald-500 bg-emerald-50',
    'warning': 'text-amber-500 bg-amber-50',
    'error': 'text-rose-500 bg-rose-50',
  };

  return (
    <div className="flex gap-3 items-start py-3 border-b border-slate-50 last:border-0">
      <div className="text-xs font-medium text-slate-400 whitespace-nowrap pt-0.5">{time}</div>
      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${typeStyles[type].split(' ')[0].replace('text', 'bg')}`} />
      <p className="text-sm text-slate-600 leading-snug">{message}</p>
    </div>
  );
};

// --- Main App ---
export default function App() {
  const [logs, setLogs] = useState([
    { id: 1, time: '10:42:05', type: 'success', message: '컨베이어 2열 양품(B) 적재 완료' },
    { id: 2, time: '10:41:30', type: 'info', message: 'AI 비전: 품종 B 인식 (신뢰도 98%)' },
    { id: 3, time: '10:38:12', type: 'warning', message: '터틀봇 1번, 목적지 도착 대기 중' },
    { id: 4, time: '10:35:00', type: 'error', message: '불량품 판별: 폐기 바구니로 이동' },
  ]);

  // 시뮬레이션용 데이터 업데이트
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      
      const randomLogs = [
        { type: 'info', message: '컨베이어 벨트 모터 절전 모드 진입' },
        { type: 'success', message: '터틀봇 배송 완료 후 복귀' },
        { type: 'info', message: 'AI 비전: 품종 A 인식 (신뢰도 95%)' },
      ];
      
      const newLog = { 
        id: Date.now(), 
        time: timeStr, 
        ...randomLogs[Math.floor(Math.random() * randomLogs.length)] 
      };
      
      setLogs(prev => [newLog, ...prev].slice(0, 8)); // 최신 8개 유지
    }, 8000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans">
      
      {/* Header */}
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Smart Farm 관제 시스템</h1>
          <p className="text-sm text-slate-500 mt-1">로봇 통합 물류 자동화 대시보드</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 text-sm font-medium px-3 py-1.5 bg-emerald-50 text-emerald-600 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            System Online
          </span>
          <button className="p-2 text-slate-400 hover:text-slate-600 bg-white rounded-lg border border-slate-200 shadow-sm transition-colors">
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (Stats & Charts) - 8 cols */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Top Stats Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCard title="오늘의 총 수확량" value="1,284" unit="개" icon={Box} trend="up" trendValue="12" />
            <StatCard title="AI 불량 검출률" value="3.2" unit="%" icon={AlertCircle} trend="down" trendValue="0.8" />
            <StatCard title="터틀봇 누적 배송" value="42" unit="회" icon={Truck} trend="up" trendValue="5" />
          </div>

          {/* Chart & Conveyor Status Area */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex-1">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <BarChart3 size={20} className="text-slate-400" />
                컨베이어 열별 적재 현황
              </h2>
              <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
                상세보기 <ChevronRight size={16} />
              </button>
            </div>
            
            {/* Simple CSS Bar Chart Mockup */}
            <div className="flex flex-col gap-5 mt-8">
              {/* Lane 1 */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-slate-600">1열 (품종 A)</span>
                  <span className="font-bold text-slate-800">450개</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-3">
                  <div className="bg-indigo-500 h-3 rounded-full" style={{ width: '75%' }}></div>
                </div>
              </div>
              {/* Lane 2 */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-slate-600">2열 (품종 B)</span>
                  <span className="font-bold text-slate-800">380개</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-3">
                  <div className="bg-sky-500 h-3 rounded-full" style={{ width: '60%' }}></div>
                </div>
              </div>
              {/* Lane 3 */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-slate-600">3열 (품종 C)</span>
                  <span className="font-bold text-slate-800">454개</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-3">
                  <div className="bg-teal-500 h-3 rounded-full" style={{ width: '80%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (Devices & Logs) - 4 cols */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Device Status */}
          <div className="flex flex-col gap-3">
            <h2 className="text-sm font-bold text-slate-500 mb-1 px-1 uppercase tracking-wider">연동 기기 상태</h2>
            <DeviceCard name="Dobot Magician" type="로봇 암 (수확/분류)" status="운영중" lastUpdate="방금 전" icon={Activity} />
            <DeviceCard name="Edge AI Camera" type="라즈베리파이 (비전 판별)" status="운영중" lastUpdate="방금 전" icon={Camera} />
            <DeviceCard name="컨베이어 벨트" type="RGB-D 센서 연동" status="대기중" lastUpdate="2분 전" icon={Box} />
            <DeviceCard name="TurtleBot 3" type="ROS2 자율주행 배송" status="대기중" lastUpdate="5분 전" icon={Truck} />
          </div>

          {/* System Logs */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex-1 flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Activity size={18} className="text-slate-500" />
                실시간 시스템 로그
              </h2>
            </div>
            <div className="p-5 flex-1 overflow-y-auto">
              <div className="flex flex-col">
                {logs.map((log) => (
                  <LogItem key={log.id} time={log.time} type={log.type} message={log.message} />
                ))}
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}