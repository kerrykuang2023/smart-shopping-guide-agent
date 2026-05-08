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

// 对话上下文状态
const contextHistory = ref<Array<{role: string, content: string}>>([]);
const chatSummary = ref<string | null>(null);

// 语音：边缘 TTS（手机扬声器播 WAV） + 浏览器 SpeechSynthesis 回退
let currentUtterance: SpeechSynthesisUtterance | null = null;
let currentTtsAudio: HTMLAudioElement | null = null;

const serverVoice = ref({ asr: false, tts: false });

async function refreshVoiceStatus() {
  try {
    const r = await fetch("/api/v1/voice/status");
    if (!r.ok) return;
    const d = await r.json();
    serverVoice.value = { asr: !!d.asr_available, tts: !!d.tts_available };
  } catch {
    serverVoice.value = { asr: false, tts: false };
  }
}

function writeWavString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
}

function pcm16ToWavBlob(samples: Int16Array, sampleRate: number): Blob {
  const n = samples.length;
  const buffer = new ArrayBuffer(44 + n * 2);
  const view = new DataView(buffer);
  writeWavString(view, 0, "RIFF");
  view.setUint32(4, 36 + n * 2, true);
  writeWavString(view, 8, "WAVE");
  writeWavString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeWavString(view, 36, "data");
  view.setUint32(40, n * 2, true);
  let o = 44;
  for (let i = 0; i < n; i++, o += 2) view.setInt16(o, samples[i]!, true);
  return new Blob([buffer], { type: "audio/wav" });
}

/** 将 MediaRecorder 生成的 webm/mp4 等转为 16kHz 单声道 WAV，供边缘 ASR */
async function mediaBlobTo16kMonoWavBlob(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new AudioContext();
  try {
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
    const sr = audioBuffer.sampleRate;
    const len = audioBuffer.length;
    const nCh = audioBuffer.numberOfChannels;
    const mono = new Float32Array(len);
    if (nCh === 1) {
      mono.set(audioBuffer.getChannelData(0));
    } else {
      for (let i = 0; i < len; i++) {
        let s = 0;
        for (let c = 0; c < nCh; c++) s += audioBuffer.getChannelData(c)[i] ?? 0;
        mono[i] = s / nCh;
      }
    }
    const targetSr = 16000;
    const outLen = Math.max(1, Math.floor((len * targetSr) / sr));
    const resampled = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const srcPos = (i * sr) / targetSr;
      const j = Math.floor(srcPos);
      const f = srcPos - j;
      const a = mono[j] ?? 0;
      const b = mono[j + 1] ?? a;
      resampled[i] = a + (b - a) * f;
    }
    const int16 = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const s = Math.max(-1, Math.min(1, resampled[i]!));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm16ToWavBlob(int16, targetSr);
  } finally {
    await ctx.close();
  }
}

function releaseCameraStream() {
  if (stream.value) {
    stream.value.getTracks().forEach((t) => t.stop());
    stream.value = null;
  }
  if (videoRef.value) videoRef.value.srcObject = null;
  isCameraReady.value = false;
}

// 初始化相机（本机摄像头预览 + 本机拍照）
async function initCamera() {
  releaseCameraStream();
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    });

    await nextTick();
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value;
      isCameraReady.value = true;
      cameraError.value = "";
    }
  } catch (e) {
    cameraError.value = "无法访问本机相机，请在浏览器中允许摄像头权限（需 HTTPS 或局域网访问）";
    console.error("Camera error:", e);
  }
}

// 识别：本机拍/选图 → 上传服务端 VLM；扫描阶段释放摄像头省资源
async function processImageRecognition(blob: Blob, filename: string) {
  releaseCameraStream();
  // 进入扫描状态
  pageState.value = 'scanning';
  scanProgress.value = 0;
  scanAngle.value = 0;
  
  // 清理上下文记忆
  contextHistory.value = [];
  chatSummary.value = null;
  
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
          text: result.value?.message || (
            '这次没能对上展台里的具体款型，常与光线或角度有关。\n您可以试试对焦笔身上的型号再拍，或直接向我提问——我一样可以帮您参谋。'
          )
        });
        void speakSmart(messages.value[0]!.text);
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
    await nextTick();
    void initCamera();
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

// 浏览器 SpeechSynthesis 回退（走本机扬声器）
function speak(text: string, onEnd?: () => void) {
  if (!('speechSynthesis' in window)) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 1.1;
  utterance.pitch = 1.05;

  const voices = window.speechSynthesis.getVoices();
  const zhVoice = voices.find((v) => v.lang.includes('zh'));
  if (zhVoice) utterance.voice = zhVoice;

  isAiSpeaking.value = true;
  currentUtterance = utterance;

  utterance.onend = () => {
    currentUtterance = null;
    isAiSpeaking.value = false;
    onEnd?.();
  };

  utterance.onerror = () => {
    currentUtterance = null;
    isAiSpeaking.value = false;
  };

  window.speechSynthesis.speak(utterance);
}

/** 优先边缘 TTS（HTMLAudio → 手机扬声器），不可用时用语义合成 */
async function speakSmart(text: string, onEnd?: () => void) {
  stopSpeaking();
  const t = text.trim();
  if (!t) {
    onEnd?.();
    return;
  }

  if (serverVoice.value.tts) {
    try {
      const resp = await fetch('/api/v1/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: t, speed: 1.0 }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.success && data.audio_base64) {
          playTtsWavBase64FromServer(t, data.audio_base64 as string, onEnd);
          return;
        }
      }
    } catch {
      /* 回退浏览器 TTS */
    }
  }

  speak(t, onEnd);
}

function playTtsWavBase64FromServer(textForFallback: string, base64: string, onEnd?: () => void) {
  try {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentTtsAudio = audio;
    isAiSpeaking.value = true;
    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentTtsAudio = null;
      isAiSpeaking.value = false;
      onEnd?.();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      currentTtsAudio = null;
      isAiSpeaking.value = false;
      speak(textForFallback, onEnd);
    };
    void audio.play().catch(() => {
      URL.revokeObjectURL(url);
      currentTtsAudio = null;
      isAiSpeaking.value = false;
      speak(textForFallback, onEnd);
    });
  } catch {
    speak(textForFallback, onEnd);
  }
}

// 停止说话（服务端 TTS 音频或浏览器播报）
function stopSpeaking() {
  if (currentTtsAudio) {
    currentTtsAudio.pause();
    currentTtsAudio.src = '';
    currentTtsAudio = null;
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  isAiSpeaking.value = false;
}

async function runChatTurn(
  userText: string,
  options?: { showUserMessage?: boolean; onChatErrorFallback?: () => string }
) {
  const showUser = options?.showUserMessage !== false;
  if (showUser) messages.value.push({ type: 'user', text: userText });

  isAiThinking.value = true;

  try {
    const requestBody: Record<string, unknown> = {
      message: userText,
      history: contextHistory.value,
      summary: chatSummary.value,
    };
    if (result.value?.recognized && result.value?.sku) requestBody.sku = result.value.sku;

    const resp = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });
    if (!resp.ok) throw new Error('chat failed');

    const data = await resp.json();
    isAiThinking.value = false;

    messages.value.push({ type: 'ai', text: data.answer });

    if (data.history) {
      contextHistory.value = data.history as typeof contextHistory.value;
    } else {
      contextHistory.value.push({ role: 'user', content: userText });
      contextHistory.value.push({ role: 'assistant', content: data.answer });
    }
    if (data.summary !== undefined) chatSummary.value = data.summary;

    void speakSmart(data.answer);
  } catch {
    isAiThinking.value = false;
    const msg = options?.onChatErrorFallback?.() ?? '抱歉，我有点走神了，能再说一遍吗？';
    messages.value.push({ type: 'ai', text: msg });
    void speakSmart(msg);
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

// 一键解读（不展示占位用户气泡，语义与打字提问一致）
async function startAiExplanation() {
  if (!result.value || !result.value.product) return;

  pageState.value = 'chat';
  await runChatTurn('请为我详细介绍一下这款产品', {
    showUserMessage: false,
    onChatErrorFallback: () => generateLocalGuide(result.value!),
  });
}

// 发送消息（本机输入法 → 服务端 LLM）
async function sendMessage() {
  const userText = inputText.value.trim();
  if (!userText) return;
  inputText.value = '';
  await runChatTurn(userText);
}

// 按住说话：本机麦克风采集 → 转成 WAV → 边缘 ASR → 再走对话链路
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

async function startVoiceInput() {
  if (pageState.value !== 'chat') return;

  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const mimePreferred = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : '';

    audioChunks = [];
    mediaRecorder = mimePreferred
      ? new MediaRecorder(audioStream, { mimeType: mimePreferred })
      : new MediaRecorder(audioStream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      audioStream.getTracks().forEach((t) => t.stop());

      const rawMime = audioChunks[0]?.type ?? mediaRecorder!.mimeType ?? 'audio/webm';
      const raw = new Blob(audioChunks, { type: rawMime });

      if (!serverVoice.value.asr) {
        messages.value.push({
          type: 'ai',
          text: '🎤 服务端语音识别不可用，请先部署 ASR 模型或使用文字提问。',
        });
        return;
      }

      if (raw.size < 900) {
        messages.value.push({ type: 'ai', text: '🎤 录音太短，请长按说完再松开。' });
        return;
      }

      let wavBlob: Blob;
      try {
        wavBlob = await mediaBlobTo16kMonoWavBlob(raw);
      } catch (err) {
        console.warn('wav encode', err);
        messages.value.push({ type: 'ai', text: '🎤 无法处理本机录音格式，请重试或改用文字。' });
        return;
      }

      isAiThinking.value = true;

      try {
        const fd = new FormData();
        fd.append('audio', wavBlob, 'speech.wav');

        const resp = await fetch('/api/v1/asr', { method: 'POST', body: fd });
        if (!resp.ok) throw new Error('asr_http');

        const asrJson: { text?: string; success?: boolean } = await resp.json();
        const text = (asrJson.text || '').trim();

        isAiThinking.value = false;

        if (!text) {
          messages.value.push({
            type: 'ai',
            text: '🎤 没有听清，请靠近麦克风再说一次。',
          });
          return;
        }

        await runChatTurn(text);
      } catch {
        isAiThinking.value = false;
        messages.value.push({ type: 'ai', text: '🎤 语音识别失败，请改用文字提问。' });
      }
    };

    mediaRecorder.start(120);
    isRecording.value = true;
  } catch (e) {
    console.error('麦克风权限或录音初始化失败:', e);
    messages.value.push({
      type: 'ai',
      text: '🎤 无法使用本机麦克风，请在浏览器中允许麦克风权限。',
    });
  }
}

function stopVoiceInput() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    isRecording.value = false;
    return;
  }
  mediaRecorder.stop();
  isRecording.value = false;
}

// 重新开始
function restart() {
  stopSpeaking();
  releaseCameraStream();
  result.value = null;
  messages.value = [];
  contextHistory.value = [];
  chatSummary.value = null;
  inputText.value = '';
  pageState.value = 'camera';
}

// 初始化：先拉语音能力状态，再等 DOM 后开本机相机
watch(
  pageState,
  async (s) => {
    if (s === 'camera') {
      await refreshVoiceStatus();
      await nextTick();
      await initCamera();
    }
    if (s === 'chat') void refreshVoiceStatus();
  },
  { flush: 'post' }
);

onMounted(async () => {
  await refreshVoiceStatus();
  await nextTick();
  await initCamera();

  if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }
});

onUnmounted(() => {
  releaseCameraStream();
  stopSpeaking();
});
</script>

<template>
  <div class="app">
    <!-- 相机页面 -->
    <div v-if="pageState === 'camera'" class="camera-page">
      <video ref="videoRef" autoplay playsinline muted class="camera-feed" />
      
      <!-- 拍照取景框 - 简洁的角落标记 -->
      <div class="focus-frame">
        <div class="corner tl"></div>
        <div class="corner tr"></div>
        <div class="corner bl"></div>
        <div class="corner br"></div>
        <div class="center-hint">
          <span>📷 对准产品</span>
        </div>
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
        <span class="chat-product-name">💬 继续为您解答</span>
        <button class="back-to-result" @click="restart">重新拍照</button>
      </div>
      
      <!-- 对话区域 -->
      <div class="chat-area">
        <!-- 初始引导（已识别商品） -->
        <div v-if="messages.length === 0 && result?.recognized" class="chat-welcome">
          <p>👋 我是您的AI导购，请问有什么可以帮您的？</p>
          <p class="hint">例如："这款笔适合学生用吗？"、"和得力的比哪个好？"</p>
        </div>
      <!-- 未识别商品的初始引导 -->
        <div v-if="messages.length === 0 && !result?.recognized" class="chat-welcome">
          <p>我没法从这张照片里对上某一款陈列笔——这很常见，不妨试试换个角度对焦型号。</p>
          <p class="hint">您可以直接问我怎么选笔、对比品牌，或使用下方麦克风/键盘继续聊。</p>
        </div>
        
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.type]">
          <div class="bubble">
            <p>{{ msg.text }}</p>
          </div>
        </div>
        
        <!-- AI思考中 - 显示专业提示 -->
        <div v-if="isAiThinking" class="message ai thinking">
          <div class="bubble thinking-bubble">
            <div class="thinking-animation">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="thinking-text">您这个问题很专业，让我思考一下...</span>
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

/* 拍照取景框 - 简洁的角落标记 */
.focus-frame {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 280px;
  height: 280px;
  pointer-events: none;
}

.focus-frame .corner {
  position: absolute;
  width: 30px;
  height: 30px;
  border: 3px solid rgba(255, 255, 255, 0.8);
}

.focus-frame .corner.tl {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
  border-radius: 8px 0 0 0;
}

.focus-frame .corner.tr {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
  border-radius: 0 8px 0 0;
}

.focus-frame .corner.bl {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
  border-radius: 0 0 0 8px;
}

.focus-frame .corner.br {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
  border-radius: 0 0 8px 0;
}

.focus-frame .center-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.focus-frame .center-hint span {
  color: rgba(255, 255, 255, 0.9);
  font-size: 16px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 16px;
  border-radius: 20px;
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
  white-space: pre-line;
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
  font-size: 14px;
  color: #a78bfa;
  font-style: italic;
}

/* 思考提示的特殊样式 */
.message.thinking .bubble.thinking-bubble {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.1));
  border: 1px solid rgba(139, 92, 246, 0.3);
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
