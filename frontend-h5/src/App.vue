<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from "vue";

type RecognizeResult = {
  sku: string | null;
  confidence: number;
  recognized: boolean;
  message: string;
  mocked: boolean;
  product: {
    name: string;
    price?: number;
    primary_image: string;
    selling_points: Array<{ text: string }>;
  } | null;
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
const scanAngle = ref(0); // 雷达扫描角度

// 对话
const messages = ref<Array<{type: 'user' | 'ai', text: string}>>([]);
const inputText = ref('');
const isRecording = ref(false);
const isAiSpeaking = ref(false);
const isAiThinking = ref(false);

// 语音合成
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

// 处理图片识别流程
async function processImageRecognition(blob: Blob, filename: string) {
  // 进入扫描状态
  pageState.value = 'scanning';
  scanProgress.value = 0;
  scanAngle.value = 0;
  
  // 模拟雷达扫描动画
  const scanInterval = setInterval(() => {
    scanAngle.value = (scanAngle.value + 3) % 360;
    scanProgress.value = Math.min(scanProgress.value + 1.5, 95);
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
    clearInterval(scanInterval);
    scanProgress.value = 100;
    
    // 延迟后进入结果页（给用户看扫描完成的感觉）
    setTimeout(() => {
      if (!result.value?.recognized) {
        // 未识别到商品库中的商品，直接进入通用对话模式
        pageState.value = 'chat';
        messages.value = [];
        // 显示友好提示
        messages.value.push({
          type: 'ai',
          text: result.value?.message || '在您的产品库中还未收录该商品，但我可以基于我的知识尽力帮您解答问题。请告诉我您想了解什么？'
        });
        // 语音播报
        speak(messages.value[0].text);
      } else {
        // 识别成功，显示产品详情
        pageState.value = 'result';
        messages.value = [];
      }
    }, 500);
    
  } catch (e) {
    clearInterval(scanInterval);
    alert('识别失败，请重试');
    pageState.value = 'camera';
  }
}

// 拍照并识别
async function captureAndRecognize() {
  if (!videoRef.value || !canvasRef.value) return;
  
  const video = videoRef.value;
  const canvas = canvasRef.value;
  
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  
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
  input.value = '';
}

// 语音合成
function speak(text: string, onEnd?: () => void) {
  if (!('speechSynthesis' in window)) return;
  
  window.speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 1.1;
  utterance.pitch = 1.05;
  
  // 尝试找中文女声
  const voices = window.speechSynthesis.getVoices();
  const zhVoice = voices.find(v => v.lang.includes('zh'));
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

// 生成AI解读内容
async function startAiExplanation() {
  if (!result.value || !result.value.product) return;
  
  // 切换到对话模式
  pageState.value = 'chat';
  
  // 先显示AI正在思考
  isAiThinking.value = true;
  
  // 构建解读请求
  try {
    const resp = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sku: result.value.sku,
        message: '请为我详细介绍一下这款产品'
      })
    });
    
    if (!resp.ok) throw new Error('请求失败');
    
    const data = await resp.json();
    isAiThinking.value = false;
    
    // 添加AI回复到对话
    messages.value.push({ type: 'ai', text: data.answer });
    
    // 语音播报
    speak(data.answer);
    
  } catch (e) {
    isAiThinking.value = false;
    // 使用本地讲解作为fallback
    const fallbackText = generateLocalGuide(result.value);
    messages.value.push({ type: 'ai', text: fallbackText });
    speak(fallbackText);
  }
}

// 生成本地讲解（fallback）
function generateLocalGuide(result: RecognizeResult): string {
  if (!result.product) return '抱歉，我暂时无法获取该商品的详细信息。';
  
  const segments = result.guide_segments;
  let text = `这是${result.product.name}。`;
  segments.forEach(seg => {
    text += `${seg.title}，${seg.text}。`;
  });
  return text;
}

// 发送消息
async function sendMessage() {
  if (!inputText.value.trim()) return;
  
  const userText = inputText.value.trim();
  messages.value.push({ type: 'user', text: userText });
  inputText.value = '';
  
  // 显示AI思考中
  isAiThinking.value = true;
  
  try {
    // 构建请求体，如果是通用对话模式（未识别商品），则不传 sku
    const requestBody: any = { message: userText };
    if (result.value?.recognized && result.value?.sku) {
      requestBody.sku = result.value.sku;
    }
    
    const resp = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    if (!resp.ok) throw new Error('请求失败');
    
    const data = await resp.json();
    isAiThinking.value = false;
    
    messages.value.push({ type: 'ai', text: data.answer });
    
    // 语音播报回复
    speak(data.answer);
    
  } catch (e) {
    isAiThinking.value = false;
    messages.value.push({
      type: 'ai',
      text: '抱歉，我有点走神了，能再说一遍吗？'
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
      
      // 语音输入暂不支持，显示提示
      messages.value.push({
        type: 'user',
        text: '🎤 [语音输入暂不支持，请使用文字]'
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
      <video ref="videoRef" autoplay playsinline muted class="camera-feed" />
      
      <!-- 雷达扫描框 -->
      <div class="radar-overlay">
        <div class="radar-frame">
          <div class="radar-circle outer"></div>
          <div class="radar-circle middle"></div>
          <div class="radar-circle inner"></div>
          <div class="radar-sweep" :style="{ transform: `rotate(${scanAngle}deg)` }"></div>
          <div class="radar-center">
            <span class="radar-icon">📡</span>
          </div>
        </div>
        <p class="radar-hint">对准产品，自动识别</p>
      </div>
      
      <div v-if="cameraError" class="camera-error">
        <p>{{ cameraError }}</p>
        <button @click="initCamera">重试</button>
      </div>
      
      <div class="camera-controls">
        <div class="controls-row">
          <button class="capture-btn" @click="captureAndRecognize" :disabled="!isCameraReady">
            <div class="btn-outer">
              <div class="btn-inner"></div>
            </div>
            <span class="btn-label">拍照</span>
          </button>
          
          <button class="gallery-btn" @click="openGallery">
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
      
      <canvas ref="canvasRef" style="display: none;" />
      <input ref="fileInputRef" type="file" accept="image/*" style="display: none" @change="handleFileSelect" />
    </div>
    
    <!-- 扫描中 -->
    <div v-if="pageState === 'scanning'" class="scanning-page">
      <div class="real-radar">
        <!-- 真实雷达效果 -->
        <div class="radar-screen">
          <div class="radar-grid"></div>
          <div class="radar-sweep-line" :style="{ transform: `rotate(${scanAngle}deg)` }"></div>
          <div class="radar-blip" :class="{ active: scanProgress > 50 }"></div>
        </div>
        <div class="scan-info">
          <p class="scan-title">正在扫描分析...</p>
          <div class="scan-progress-bar">
            <div class="scan-progress-fill" :style="{ width: scanProgress + '%' }"></div>
          </div>
          <p class="scan-percent">{{ Math.round(scanProgress) }}%</p>
        </div>
      </div>
    </div>
    
    <!-- 结果页面 -->
    <div v-if="pageState === 'result'" class="result-page">
      <div v-if="result?.product" class="result-header">
        <img :src="result.product.primary_image" :alt="result.product.name" class="product-image" />
        <div class="product-info">
          <h1>{{ result.product.name }}</h1>
          <p class="price" v-if="result.product.price">¥{{ result.product.price }}</p>
          <div class="badges">
            <span class="badge">{{ result.sku }}</span>
            <span class="badge confidence">置信度 {{ (result.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
      
      <!-- 关键交互按钮 -->
      <div v-if="result?.product" class="guide-action-section">
        <p class="guide-hint">已识别产品，需要详细解读吗？</p>
        <button class="guide-btn" @click="startAiExplanation" :disabled="isAiThinking">
          <span class="btn-icon">🎯</span>
          <span class="btn-text">需要帮我解读一下吗？</span>
        </button>
      </div>
      
      <!-- 产品卖点预览 -->
      <div v-if="result?.product && result.guide_segments.length > 0" class="guide-preview">
        <div v-for="(seg, idx) in result.guide_segments.slice(0, 2)" :key="idx" class="preview-card">
          <h4>{{ seg.title }}</h4>
          <p>{{ seg.text.substring(0, 50) }}...</p>
        </div>
      </div>
      
      <button class="restart-btn" @click="restart">
        📷 识别其他产品
      </button>
    </div>
    
    <!-- 对话页面 -->
    <div v-if="pageState === 'chat'" class="chat-page">
      <!-- 产品信息条（已识别商品时显示） -->
      <div v-if="result?.product" class="chat-header">
        <img :src="result.product.primary_image" class="chat-product-thumb" />
        <span class="chat-product-name">{{ result.product.name }}</span>
        <button class="back-to-result" @click="pageState = 'result'">返回</button>
      </div>
      <!-- 通用对话头部（未识别商品时显示） -->
      <div v-else class="chat-header general">
        <span class="chat-product-name">💬 通用咨询</span>
        <button class="back-to-result" @click="restart">重新拍照</button>
      </div>
      
      <!-- 对话区域 -->
      <div class="chat-area">
        <!-- 初始引导（已识别商品） -->
        <div v-if="messages.length === 0 && result?.recognized" class="chat-welcome">
          <p>👋 我是您的AI导购，请问有什么可以帮您的？</p>
          <p class="hint">例如："这款笔适合学生用吗？"、"和得力的比哪个好？"</p>
        </div>
        <!-- 初始引导（未识别商品 - 通用对话模式） -->
        <div v-if="messages.length === 0 && !result?.recognized" class="chat-welcome">
          <p>🔍 这个商品不在我的产品库中</p>
          <p class="hint">但我可以基于通用知识帮您解答问题，请直接输入您想了解的内容</p>
        </div>
        
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.type]">
          <div class="bubble">
            <p>{{ msg.text }}</p>
          </div>
        </div>
        
        <!-- AI思考中 -->
        <div v-if="isAiThinking" class="message ai thinking">
          <div class="bubble">
            <div class="thinking-animation">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="thinking-text">AI思考中...</span>
          </div>
        </div>
        
        <!-- AI说话中 -->
        <div v-if="isAiSpeaking" class="ai-speaking-bar" @click="stopSpeaking">
          <div class="sound-waves">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span>点击打断</span>
        </div>
      </div>
      
      <!-- 输入区 -->
      <div class="chat-input-area">
        <div class="input-wrapper">
          <input
            v-model="inputText"
            placeholder="输入您的问题..."
            @keyup.enter="sendMessage"
          />
          <button 
            class="voice-btn-small"
            @mousedown="startVoiceInput"
            @mouseup="stopVoiceInput"
            :class="{ recording: isRecording }"
          >
            🎤
          </button>
          <button 
            class="send-btn"
            @click="sendMessage"
            :disabled="!inputText.trim() || isAiThinking"
          >
            发送
          </button>
        </div>
        <button class="restart-btn-small" @click="restart">
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

/* 雷达扫描框 - 飞机雷达风格 */
.radar-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.radar-frame {
  width: 260px;
  height: 260px;
  position: relative;
}

.radar-circle {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(59, 130, 246, 0.5);
}

.radar-circle.outer {
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  animation: radarPulse 2s ease-out infinite;
}

.radar-circle.middle {
  width: 66%;
  height: 66%;
  top: 17%;
  left: 17%;
  border-color: rgba(59, 130, 246, 0.4);
}

.radar-circle.inner {
  width: 33%;
  height: 33%;
  top: 33.5%;
  left: 33.5%;
  border-color: rgba(59, 130, 246, 0.6);
}

@keyframes radarPulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.1); opacity: 0; }
}

/* 雷达扫描线 - 旋转效果 */
.radar-sweep {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 50%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6, #60a5fa);
  transform-origin: 0 50%;
  box-shadow: 0 0 10px #3b82f6;
  animation: radarRotate 3s linear infinite;
}

@keyframes radarRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.radar-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-icon {
  font-size: 12px;
}

.radar-hint {
  color: rgba(255,255,255,0.9);
  font-size: 15px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  letter-spacing: 1px;
}

/* 底部控制 */
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

.capture-btn, .gallery-btn {
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.btn-outer {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-inner {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: white;
}

.gallery-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.gallery-icon svg {
  width: 24px;
  height: 24px;
  color: white;
}

.btn-label {
  color: white;
  font-size: 12px;
}

.btn-hint {
  color: rgba(255,255,255,0.7);
  font-size: 13px;
}

/* ===== 扫描中页面 - 真实雷达效果 ===== */
.scanning-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #0a0f1a 0%, #0f172a 100%);
}

.real-radar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
}

.radar-screen {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(16, 42, 67, 0.9) 0%, rgba(10, 15, 26, 1) 100%);
  position: relative;
  border: 2px solid rgba(59, 130, 246, 0.3);
  overflow: hidden;
}

.radar-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    repeating-radial-gradient(circle at center, transparent 0, transparent 30px, rgba(59, 130, 246, 0.1) 31px);
}

.radar-grid::before,
.radar-grid::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(59, 130, 246, 0.2);
}

.radar-grid::after {
  transform: rotate(90deg);
}

.radar-sweep-line {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 50%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6);
  transform-origin: 0 50%;
  box-shadow: 0 0 8px #3b82f6;
}

.radar-blip {
  position: absolute;
  top: 30%;
  right: 30%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  opacity: 0;
  transition: opacity 0.3s;
}

.radar-blip.active {
  opacity: 1;
  animation: blipPulse 1s ease-out infinite;
}

@keyframes blipPulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.scan-info {
  text-align: center;
}

.scan-title {
  color: #93c5fd;
  font-size: 18px;
  margin-bottom: 16px;
}

.scan-progress-bar {
  width: 250px;
  height: 4px;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  overflow: hidden;
}

.scan-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width 0.1s;
}

.scan-percent {
  color: #60a5fa;
  font-size: 32px;
  font-weight: 700;
  margin-top: 16px;
}

/* ===== 结果页面 ===== */
.result-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  color: white;
  padding: 20px;
  overflow-y: auto;
}

.result-header {
  display: flex;
  gap: 15px;
  padding: 15px;
  background: rgba(255,255,255,0.05);
  border-radius: 16px;
  margin-bottom: 20px;
}

.product-image {
  width: 100px;
  height: 100px;
  object-fit: contain;
  border-radius: 12px;
  background: white;
  padding: 10px;
}

.product-info h1 {
  font-size: 20px;
  margin-bottom: 8px;
}

.price {
  font-size: 24px;
  color: #fbbf24;
  font-weight: 700;
}

.badges {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.badge {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.3);
  border-radius: 20px;
  font-size: 12px;
}

/* 关键交互区域 */
.guide-action-section {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 20px;
  padding: 24px;
  text-align: center;
  margin-bottom: 20px;
}

.guide-hint {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  margin-bottom: 16px;
}

.guide-btn {
  width: 100%;
  padding: 16px 24px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  border-radius: 16px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform 0.2s;
}

.guide-btn:active {
  transform: scale(0.98);
}

.guide-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 20px;
}

/* 卖点预览 */
.guide-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.preview-card {
  background: rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
}

.preview-card h4 {
  color: #60a5fa;
  font-size: 15px;
  margin-bottom: 8px;
}

.preview-card p {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
}

.restart-btn {
  width: 100%;
  padding: 14px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  color: rgba(255,255,255,0.8);
  font-size: 15px;
  cursor: pointer;
}

/* ===== 对话页面 ===== */
.chat-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  color: white;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.chat-product-thumb {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border-radius: 8px;
  background: white;
  padding: 4px;
}

.chat-product-name {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
}

.back-to-result {
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 8px;
  color: white;
  font-size: 13px;
  cursor: pointer;
}

/* 通用对话头部 */
.chat-header.general {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(59, 130, 246, 0.2));
  border-bottom: 1px solid rgba(139, 92, 246, 0.3);
}

.chat-header.general .chat-product-name {
  color: #a78bfa;
  font-weight: 600;
}

/* 对话区域 */
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chat-welcome {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255,255,255,0.6);
}

.chat-welcome .hint {
  font-size: 13px;
  margin-top: 12px;
  color: rgba(255,255,255,0.4);
}

.message {
  display: flex;
  margin-bottom: 16px;
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

.message.thinking .bubble {
  display: flex;
  align-items: center;
  gap: 8px;
}

.thinking-animation {
  display: flex;
  gap: 4px;
}

.thinking-animation .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #93c5fd;
  animation: thinkingBounce 1.4s infinite;
}

.thinking-animation .dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-animation .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes thinkingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.thinking-text {
  font-size: 13px;
  color: #93c5fd;
}

/* AI说话条 */
.ai-speaking-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  margin: 12px 16px;
  cursor: pointer;
}

.sound-waves {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 20px;
}

.sound-waves span {
  width: 3px;
  background: #3b82f6;
  border-radius: 2px;
  animation: soundWave 0.5s ease-in-out infinite;
}

.sound-waves span:nth-child(1) { height: 8px; animation-delay: 0s; }
.sound-waves span:nth-child(2) { height: 14px; animation-delay: 0.1s; }
.sound-waves span:nth-child(3) { height: 20px; animation-delay: 0.2s; }
.sound-waves span:nth-child(4) { height: 14px; animation-delay: 0.3s; }
.sound-waves span:nth-child(5) { height: 8px; animation-delay: 0.4s; }

@keyframes soundWave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

.ai-speaking-bar span {
  font-size: 13px;
  color: #93c5fd;
}

/* 输入区 */
.chat-input-area {
  padding: 12px 16px 20px;
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(255,255,255,0.1);
}

.input-wrapper {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.input-wrapper input {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 24px;
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 15px;
}

.input-wrapper input::placeholder {
  color: rgba(255,255,255,0.5);
}

.voice-btn-small {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 18px;
  cursor: pointer;
}

.voice-btn-small.recording {
  background: #ef4444;
}

.send-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 24px;
  background: #3b82f6;
  color: white;
  font-weight: 500;
  cursor: pointer;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.restart-btn-small {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  background: transparent;
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  cursor: pointer;
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
  cursor: pointer;
}
</style>
