<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";

type RecognizeResult = {
  sku: string;
  confidence: number;
  mocked: boolean;
  product: {
    name: string;
    price?: number;
    primary_image: string;
    selling_points: Array<{ text: string }>;
  };
  guide_segments: Array<{ title: string; text: string }>;
  related_products: Array<{ name: string; image: string; price?: number }>;
};

// 页面状态
const pageState = ref<'camera' | 'scanning' | 'result' | 'chat'>('camera');

// 相机相关
const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const stream = ref<MediaStream | null>(null);
const isCameraReady = ref(false);
const cameraError = ref('');

// 识别结果
const result = ref<RecognizeResult | null>(null);
const scanProgress = ref(0);
const scanningText = ref('正在识别...');

// AI思考状态文字
const thinkingTexts = [
  '正在分析图像...',
  '提取产品特征...',
  '检索知识库...',
  '构建回复内容...',
  '即将完成...'
];
const thinkingIndex = ref(0);
let thinkingInterval: ReturnType<typeof setInterval> | null = null;

// AI对话思考中
const isAiThinking = ref(false);

// 对话
const messages = ref<Array<{type: 'user' | 'ai', text: string, audioUrl?: string}>>([]);
const inputText = ref('');
const isRecording = ref(false);
const isAiSpeaking = ref(false);

// 语音合成
let synth: SpeechSynthesis | null = null;
let currentUtterance: SpeechSynthesisUtterance | null = null;

// 初始化相机
async function initCamera() {
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { 
        facingMode: 'environment',
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    });
    
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value;
      isCameraReady.value = true;
      cameraError.value = '';
    }
  } catch (e) {
    cameraError.value = '无法访问相机，请检查权限';
    console.error('Camera error:', e);
  }
}

// 开始AI思考动画
function startThinkingAnimation() {
  thinkingIndex.value = 0;
  if (thinkingInterval) clearInterval(thinkingInterval);
  thinkingInterval = setInterval(() => {
    thinkingIndex.value = (thinkingIndex.value + 1) % thinkingTexts.length;
  }, 1500);
}

function stopThinkingAnimation() {
  if (thinkingInterval) {
    clearInterval(thinkingInterval);
    thinkingInterval = null;
  }
}

// 处理图片识别流程
async function processImageRecognition(blob: Blob, filename: string) {
  // 进入扫描状态
  pageState.value = 'scanning';
  startThinkingAnimation();
  
  // 扫描动画
  scanProgress.value = 0;
  const progressInterval = setInterval(() => {
    scanProgress.value += 1.5;
    if (scanProgress.value >= 95) {
      clearInterval(progressInterval);
    }
  }, 50);
  
  try {
    // 发送识别请求
    const formData = new FormData();
    formData.append('image', blob, filename);
    
    const resp = await fetch('/api/v1/recognize', { 
      method: 'POST', 
      body: formData 
    });
    
    if (!resp.ok) throw new Error('识别失败');
    
    result.value = await resp.json();
    scanProgress.value = 100;
    stopThinkingAnimation();
    
    // 进入结果页
    setTimeout(() => {
      pageState.value = 'result';
      // AI自动开口
      nextTick(() => {
        const guideText = formatGuideText(result.value!);
        speak(guideText, () => {
          // 讲完后自动进入对话模式
          setTimeout(() => {
            pageState.value = 'chat';
          }, 500);
        });
      });
    }, 500);
    
  } catch (e) {
    stopThinkingAnimation();
    scanningText.value = '识别失败，请重试';
    setTimeout(() => {
      pageState.value = 'camera';
      scanningText.value = '正在识别...';
    }, 1500);
  }
}

// 拍照并识别
async function captureAndRecognize() {
  if (!videoRef.value || !canvasRef.value) return;
  
  const video = videoRef.value;
  const canvas = canvasRef.value;
  
  // 设置canvas尺寸
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  
  // 绘制视频帧
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  // 转换为blob
  const blob = await new Promise<Blob>((resolve) => {
    canvas.toBlob((b) => resolve(b!), 'image/jpeg', 0.9);
  });
  
  await processImageRecognition(blob, 'capture.jpg');
}

// 从相册选择图片
function openGallery() {
  fileInputRef.value?.click();
}

// 处理选择的文件
async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  
  await processImageRecognition(file, file.name);
  
  // 清空input以便可以再次选择同一文件
  input.value = '';
}

// 格式化讲解文本
function formatGuideText(data: RecognizeResult): string {
  const segments = data.guide_segments;
  let text = `这是${data.product.name}。`;
  segments.forEach(seg => {
    text += `${seg.title}，${seg.text}。`;
  });
  return text;
}

// 语音合成
function speak(text: string, onEnd?: () => void) {
  if (!('speechSynthesis' in window)) return;
  
  // 停止之前的
  window.speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 1.1;
  utterance.pitch = 1.05;
  
  // 尝试找中文女声
  const voices = window.speechSynthesis.getVoices();
  const zhVoice = voices.find(v => v.lang.includes('zh') && v.name.includes('Female'));
  if (zhVoice) utterance.voice = zhVoice;
  
  isAiSpeaking.value = true;
  currentUtterance = utterance;
  
  utterance.onend = () => {
    isAiSpeaking.value = false;
    onEnd?.();
  };
  
  utterance.onerror = () => {
    isAiSpeaking.value = false;
  };
  
  window.speechSynthesis.speak(utterance);
}

// 停止说话
function stopSpeaking() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    isAiSpeaking.value = false;
  }
}

// 发送消息
async function sendMessage() {
  if (!inputText.value.trim() || !result.value) return;
  
  const userText = inputText.value.trim();
  messages.value.push({ type: 'user', text: userText });
  inputText.value = '';
  
  try {
    const resp = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        sku: result.value.sku, 
        message: userText 
      }),
    });
    
    if (!resp.ok) throw new Error('请求失败');
    
    const data = await resp.json();
    messages.value.push({ type: 'ai', text: data.answer });
    
    // AI语音回复
    speak(data.answer);
    
  } catch (e) {
    messages.value.push({ 
      type: 'ai', 
      text: '抱歉，我没听清楚，能再说一遍吗？' 
    });
  }
}

// 按住说话
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

async function startVoiceInput() {
  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(audioStream);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      audioStream.getTracks().forEach(t => t.stop());
      
      // TODO: 发送语音识别（简化版先用文字）
      messages.value.push({ 
        type: 'user', 
        text: '🎤 [语音输入]' 
      });
    };
    
    mediaRecorder.start();
    isRecording.value = true;
  } catch (e) {
    console.error('录音失败:', e);
  }
}

function stopVoiceInput() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    isRecording.value = false;
  }
}

// 重新开始
function restart() {
  stopSpeaking();
  result.value = null;
  messages.value = [];
  inputText.value = '';
  pageState.value = 'camera';
  initCamera();
}

// 初始化
onMounted(() => {
  initCamera();
  
  // 预加载语音
  if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
  }
});

onUnmounted(() => {
  if (stream.value) {
    stream.value.getTracks().forEach(t => t.stop());
  }
  stopSpeaking();
});
</script>

<template>
  <div class="app">
    <!-- 相机页面 -->
    <div v-if="pageState === 'camera'" class="camera-page">
      <!-- 视频流 -->
      <video 
        ref="videoRef" 
        autoplay 
        playsinline
        muted
        class="camera-feed"
      />
      
      <!-- 扫描框 -->
      <div class="scan-overlay">
        <div class="scan-frame">
          <div class="corner tl"></div>
          <div class="corner tr"></div>
          <div class="corner bl"></div>
          <div class="corner br"></div>
          <div class="scan-line"></div>
        </div>
        <p class="scan-hint">对准产品，自动识别</p>
      </div>
      
      <!-- 错误提示 -->
      <div v-if="cameraError" class="camera-error">
        <p>{{ cameraError }}</p>
        <button @click="initCamera">重试</button>
      </div>
      
      <!-- 底部按钮 -->
      <div class="camera-controls">
        <div class="controls-row">
          <!-- 拍照按钮 -->
          <button 
            class="capture-btn"
            @click="captureAndRecognize"
            :disabled="!isCameraReady"
          >
            <div class="btn-outer">
              <div class="btn-inner"></div>
            </div>
            <span class="btn-label">拍照</span>
          </button>
          
          <!-- 相册按钮 -->
          <button 
            class="gallery-btn"
            @click="openGallery"
          >
            <div class="gallery-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </div>
            <span class="btn-label">相册</span>
          </button>
        </div>
        <p class="btn-hint">拍照或从相册选择图片</p>
      </div>
      
      <!-- 隐藏的画布 -->
      <canvas ref="canvasRef" style="display: none;" />
      
      <!-- 隐藏的文件选择input -->
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        style="display: none"
        @change="handleFileSelect"
      />
    </div>
    
    <!-- 扫描中 / AI思考中 -->
    <div v-if="pageState === 'scanning'" class="scanning-page">
      <div class="ai-brain">
        <!-- 中央大脑核心 -->
        <div class="brain-core">
          <div class="core-pulse"></div>
          <div class="core-inner"></div>
          <div class="core-glow"></div>
        </div>
        
        <!-- 环绕的轨道环 -->
        <div class="orbit-ring ring-1">
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
        </div>
        <div class="orbit-ring ring-2">
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
        </div>
        <div class="orbit-ring ring-3">
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
          <div class="orbit-particle"></div>
        </div>
        
        <!-- 雷达扫描线 -->
        <div class="radar-scan"></div>
        <div class="radar-grid"></div>
        
        <!-- 数据流粒子 -->
        <div class="data-particles">
          <span v-for="i in 20" :key="i" class="particle" :style="{
            left: Math.random() * 100 + '%',
            animationDelay: Math.random() * 2 + 's',
            animationDuration: (1 + Math.random() * 2) + 's'
          }"></span>
        </div>
        
        <!-- 思考状态文字 -->
        <div class="thinking-status">
          <p class="thinking-line">{{ thinkingTexts[thinkingIndex] }}</p>
          <div class="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
        
        <!-- 进度环 -->
        <div class="progress-ring">
          <svg viewBox="0 0 100 100">
            <defs>
              <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:1" />
                <stop offset="50%" style="stop-color:#8b5cf6;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:1" />
              </linearGradient>
            </defs>
            <circle 
              class="progress-bg" 
              cx="50" cy="50" r="45"
            />
            <circle 
              class="progress-fill" 
              cx="50" cy="50" r="45"
              :style="{ strokeDashoffset: 283 - (283 * scanProgress / 100) }"
            />
          </svg>
          <span class="progress-text">{{ Math.round(scanProgress) }}%</span>
        </div>
        
        <!-- 底部状态信息 -->
        <div class="status-info">
          <div class="status-item" :class="{ active: scanProgress > 20 }">
            <span class="icon">📡</span>
            <span>图像接收</span>
          </div>
          <div class="status-item" :class="{ active: scanProgress > 40 }">
            <span class="icon">🔍</span>
            <span>特征提取</span>
          </div>
          <div class="status-item" :class="{ active: scanProgress > 60 }">
            <span class="icon">🧠</span>
            <span>模型推理</span>
          </div>
          <div class="status-item" :class="{ active: scanProgress > 80 }">
            <span class="icon">💡</span>
            <span>生成回复</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 结果/对话页面 -->
    <div v-if="pageState === 'result' || pageState === 'chat'" class="result-page">
      <!-- 顶部产品信息 -->
      <div class="product-header">
        <img 
          :src="result?.product.primary_image" 
          :alt="result?.product.name"
          class="product-image"
        />
        <div class="product-info">
          <h1>{{ result?.product.name }}</h1>
          <p class="price" v-if="result?.product.price">
            ¥{{ result.product.price }}
          </p>
          <div class="badges">
            <span class="badge">{{ result?.sku }}</span>
            <span class="badge confidence">
              置信度 {{ (result?.confidence || 0 * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
      
      <!-- AI说话动画 -->
      <div v-if="isAiSpeaking" class="ai-speaking-indicator" @click="stopSpeaking">
        <div class="sound-waves">
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p>AI 正在讲解，点击打断</p>
      </div>
      
      <!-- 讲解内容（简洁版） -->
      <div v-if="pageState === 'result'" class="guide-content">
        <div 
          v-for="(seg, idx) in result?.guide_segments" 
          :key="idx"
          class="guide-card"
          :style="{ animationDelay: idx * 0.1 + 's' }"
        >
          <h3>{{ seg.title }}</h3>
          <p>{{ seg.text }}</p>
        </div>
      </div>
      
      <!-- 对话区域 -->
      <div v-if="pageState === 'chat'" class="chat-area">
        <div class="messages">
          <div 
            v-for="(msg, idx) in messages" 
            :key="idx"
            :class="['message', msg.type]"
          >
            <div class="bubble">
              <p>{{ msg.text }}</p>
            </div>
          </div>
          <div v-if="isAiSpeaking" class="message ai typing">
            <div class="bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 底部输入区 -->
      <div class="input-area">
        <div class="input-container">
          <input
            v-model="inputText"
            placeholder="问我关于这个产品的问题..."
            @keyup.enter="sendMessage"
          />
          <button 
            class="voice-btn"
            @mousedown="startVoiceInput"
            @mouseup="stopVoiceInput"
            @touchstart.prevent="startVoiceInput"
            @touchend.prevent="stopVoiceInput"
            :class="{ recording: isRecording }"
          >
            <span v-if="!isRecording">🎤</span>
            <span v-else>⏹️</span>
          </button>
          <button 
            class="send-btn"
            @click="sendMessage"
            :disabled="!inputText.trim()"
          >
            发送
          </button>
        </div>
        <button class="restart-btn" @click="restart">
          📷 识别其他产品
        </button>
      </div>
    </div>
  </div>
</template>

<style>
/* ===== 基础样式 ===== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #000;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ===== 相机页面 ===== */
.camera-page {
  width: 100%;
  height: 100%;
  position: relative;
  background: #000;
}

.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 扫描框 */
.scan-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.scan-frame {
  width: 280px;
  height: 280px;
  position: relative;
}

.corner {
  position: absolute;
  width: 40px;
  height: 40px;
  border: 4px solid #3b82f6;
}

.corner.tl { top: 0; left: 0; border-right: none; border-bottom: none; }
.corner.tr { top: 0; right: 0; border-left: none; border-bottom: none; }
.corner.bl { bottom: 0; left: 0; border-right: none; border-top: none; }
.corner.br { bottom: 0; right: 0; border-left: none; border-top: none; }

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6, transparent);
  animation: scan 2s linear infinite;
  box-shadow: 0 0 10px #3b82f6;
}

@keyframes scan {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

.scan-hint {
  color: rgba(255,255,255,0.9);
  font-size: 15px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  letter-spacing: 1px;
}

/* 错误提示 */
.camera-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: white;
  background: rgba(0,0,0,0.8);
  padding: 30px;
  border-radius: 16px;
}

.camera-error button {
  margin-top: 15px;
  padding: 10px 30px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
}

/* 底部控制区 */
.camera-controls {
  position: absolute;
  bottom: 40px;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.controls-row {
  display: flex;
  align-items: center;
  gap: 40px;
}

.capture-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.btn-outer {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s;
}

.capture-btn:active .btn-outer {
  transform: scale(0.95);
}

.btn-inner {
  width: 65px;
  height: 65px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 2px 10px rgba(0,0,0,0.3);
}

.gallery-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.gallery-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  border: 2px solid rgba(255,255,255,0.3);
}

.gallery-icon svg {
  width: 28px;
  height: 28px;
  color: white;
}

.gallery-btn:active .gallery-icon {
  transform: scale(0.95);
  background: rgba(255,255,255,0.3);
}

.btn-label {
  color: white;
  font-size: 12px;
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

.btn-hint {
  color: rgba(255,255,255,0.7);
  font-size: 13px;
}

/* ===== 扫描中页面 ===== */
.scanning-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
}

.scanning-animation {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 30px;
}

.spinner {
  position: relative;
  width: 100px;
  height: 100px;
}

.ring {
  position: absolute;
  border: 3px solid transparent;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1.5s linear infinite;
}

.ring:nth-child(1) {
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}

.ring:nth-child(2) {
  width: 70%;
  height: 70%;
  top: 15%;
  left: 15%;
  animation-direction: reverse;
  animation-duration: 1.2s;
  border-top-color: #60a5fa;
}

.ring:nth-child(3) {
  width: 40%;
  height: 40%;
  top: 30%;
  left: 30%;
  animation-duration: 0.8s;
  border-top-color: #93c5fd;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-bar {
  width: 200px;
  height: 4px;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 2px;
  transition: width 0.3s;
}

.scanning-text {
  color: white;
  font-size: 16px;
  letter-spacing: 2px;
}

/* ===== 结果/对话页面 ===== */
.result-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  color: white;
}

/* 产品头部 */
.product-header {
  display: flex;
  gap: 15px;
  padding: 20px;
  background: rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.product-image {
  width: 100px;
  height: 100px;
  object-fit: contain;
  border-radius: 12px;
  background: white;
  padding: 10px;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.product-info h1 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: white;
}

.price {
  font-size: 24px;
  color: #fbbf24;
  font-weight: 700;
  margin-bottom: 8px;
}

.badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.3);
  border-radius: 20px;
  font-size: 12px;
  color: #93c5fd;
}

.badge.confidence {
  background: rgba(34, 197, 94, 0.3);
  color: #86efac;
}

/* AI说话指示器 */
.ai-speaking-indicator {
  padding: 15px 20px;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.2), transparent);
  border-left: 3px solid #3b82f6;
  display: flex;
  align-items: center;
  gap: 15px;
  cursor: pointer;
}

.sound-waves {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 24px;
}

.sound-waves span {
  width: 4px;
  background: #3b82f6;
  border-radius: 2px;
  animation: wave 0.5s ease-in-out infinite;
}

.sound-waves span:nth-child(1) { height: 8px; animation-delay: 0s; }
.sound-waves span:nth-child(2) { height: 16px; animation-delay: 0.1s; }
.sound-waves span:nth-child(3) { height: 24px; animation-delay: 0.2s; }
.sound-waves span:nth-child(4) { height: 16px; animation-delay: 0.3s; }
.sound-waves span:nth-child(5) { height: 8px; animation-delay: 0.4s; }

@keyframes wave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

.ai-speaking-indicator p {
  color: #93c5fd;
  font-size: 14px;
}

/* 讲解内容 */
.guide-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guide-card {
  background: rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.1);
  animation: slideIn 0.4s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes slideIn {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.guide-card h3 {
  font-size: 16px;
  color: #60a5fa;
  margin-bottom: 8px;
  font-weight: 600;
}

.guide-card p {
  font-size: 15px;
  line-height: 1.6;
  color: rgba(255,255,255,0.9);
}

/* 对话区域 */
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.ai {
  justify-content: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 20px;
  font-size: 15px;
  line-height: 1.5;
}

.message.user .bubble {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.ai .bubble {
  background: rgba(255,255,255,0.1);
  color: white;
  border-bottom-left-radius: 4px;
}

.message.ai.typing .bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px 20px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #93c5fd;
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

/* 输入区 */
.input-area {
  padding: 15px 20px 25px;
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(255,255,255,0.1);
}

.input-container {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.input-container input {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 24px;
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 15px;
  outline: none;
}

.input-container input::placeholder {
  color: rgba(255,255,255,0.5);
}

.voice-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.voice-btn.recording {
  background: #ef4444;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.send-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 24px;
  background: #3b82f6;
  color: white;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.restart-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  background: transparent;
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.restart-btn:hover {
  background: rgba(255,255,255,0.1);
}
</style>
