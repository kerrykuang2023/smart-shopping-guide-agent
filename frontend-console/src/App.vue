<script setup lang="ts">
import { onMounted, ref } from "vue";

type Health = {
  status: string;
  demo_mode: boolean;
  loaded_products: number;
  vlm_provider: string;
};

type Product = {
  sku: string;
  name: string;
  brand: string;
  price?: number;
};

type Settings = {
  public_base_url: string;
  vlm_base_url: string;
  vlm_api_key: string;
  vlm_model: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  qdrant_url: string;
  qdrant_api_key: string;
  apphub_url: string;
  tts_base_url: string;
  tts_api_key: string;
  tts_model: string;
  asr_base_url: string;
  asr_api_key: string;
  asr_model: string;
};

const healthText = ref("加载中...");
const products = ref<Product[]>([]);
const settings = ref<Settings>({
  public_base_url: "",
  vlm_base_url: "",
  vlm_api_key: "",
  vlm_model: "GLM-4.5V",
  llm_base_url: "",
  llm_api_key: "",
  llm_model: "qwen-plus",
  qdrant_url: "",
  qdrant_api_key: "",
  apphub_url: "",
  tts_base_url: "",
  tts_api_key: "",
  tts_model: "cosyvoice",
  asr_base_url: "",
  asr_api_key: "",
  asr_model: "sensevoice",
});
const saveHint = ref("");
const qrUrl = "/api/v1/qrcode?size=320";

// Test connection states
const testStates = ref<Record<string, { status: "idle" | "testing" | "success" | "error"; message: string; latency?: number }>>({
  vlm: { status: "idle", message: "" },
  llm: { status: "idle", message: "" },
  tts: { status: "idle", message: "" },
  asr: { status: "idle", message: "" },
});

async function load() {
  const h = (await (await fetch("/api/v1/health")).json()) as Health;
  healthText.value = `状态: ${h.status} | DemoMode: ${h.demo_mode} | SKU: ${h.loaded_products} | VLM: ${h.vlm_provider}`;

  const p = await (await fetch("/api/v1/products")).json();
  products.value = p.items || [];

  settings.value = (await (await fetch("/api/v1/settings")).json()) as Settings;
}

async function saveSettings() {
  saveHint.value = "保存中...";
  const resp = await fetch("/api/v1/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings.value),
  });
  saveHint.value = resp.ok ? "已保存" : "保存失败";
}

async function testConnection(serviceType: "vlm" | "llm" | "tts" | "asr") {
  testStates.value[serviceType] = { status: "testing", message: "测试中..." };
  try {
    const resp = await fetch("/api/v1/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_type: serviceType }),
    });
    const data = await resp.json();
    if (data.success) {
      testStates.value[serviceType] = {
        status: "success",
        message: `✓ ${data.message} (${data.latency_ms}ms)`,
        latency: data.latency_ms,
      };
    } else {
      testStates.value[serviceType] = {
        status: "error",
        message: `✗ ${data.message} (${data.latency_ms}ms)`,
        latency: data.latency_ms,
      };
    }
  } catch (e) {
    testStates.value[serviceType] = {
      status: "error",
      message: `✗ 请求失败: ${String(e)}`,
    };
  }
}

onMounted(load);
</script>

<template>
  <div class="wrap">
    <h1>KWeaver Box · 智能导购 Console</h1>
    <div class="row">
      <div class="card" style="flex: 2">
        <h2>服务状态</h2>
        <p class="muted">{{ healthText }}</p>
      </div>
      <div class="card" style="flex: 1">
        <h2>移动端入口</h2>
        <img :src="qrUrl" alt="QR Code" style="width: 280px; height: 280px; background: white; padding: 8px; border-radius: 8px" />
      </div>
    </div>

    <div class="card">
      <h2>SKU 列表</h2>
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>名称</th>
            <th>品牌</th>
            <th>价格</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in products" :key="p.sku">
            <td>{{ p.sku }}</td>
            <td>{{ p.name }}</td>
            <td>{{ p.brand }}</td>
            <td>{{ p.price ? `¥${p.price}` : "-" }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>配置中心（模型服务配置）</h2>
      <p class="muted">配置外部 AI 服务地址，点击"测试"验证连接。</p>
      <div style="display: grid; gap: 8px; max-width: 760px">
        <label>Public Base URL（手机扫码访问地址） <input v-model="settings.public_base_url" placeholder="http://192.168.x.x:8080" /></label>
        
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end;">
          <label>VLM Base URL <input v-model="settings.vlm_base_url" placeholder="https://api.edgefn.net" /></label>
          <button @click="testConnection('vlm')" :disabled="testStates.vlm.status === 'testing'" style="height: 32px; min-width: 80px;">
            {{ testStates.vlm.status === 'testing' ? '测试中...' : '测试' }}
          </button>
        </div>
        <div v-if="testStates.vlm.status !== 'idle'" :style="{ color: testStates.vlm.status === 'success' ? '#28a745' : testStates.vlm.status === 'error' ? '#dc3545' : '#666', fontSize: '12px', marginTop: '-4px', marginBottom: '4px' }">
          {{ testStates.vlm.message }}
        </div>
        <label>VLM API Key <input v-model="settings.vlm_api_key" type="password" /></label>
        <label>VLM Model <input v-model="settings.vlm_model" placeholder="GLM-4.5V" /></label>
        
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; margin-top: 8px;">
          <label>LLM Base URL <input v-model="settings.llm_base_url" /></label>
          <button @click="testConnection('llm')" :disabled="testStates.llm.status === 'testing'" style="height: 32px; min-width: 80px;">
            {{ testStates.llm.status === 'testing' ? '测试中...' : '测试' }}
          </button>
        </div>
        <div v-if="testStates.llm.status !== 'idle'" :style="{ color: testStates.llm.status === 'success' ? '#28a745' : testStates.llm.status === 'error' ? '#dc3545' : '#666', fontSize: '12px', marginTop: '-4px', marginBottom: '4px' }">
          {{ testStates.llm.message }}
        </div>
        <label>LLM API Key <input v-model="settings.llm_api_key" type="password" /></label>
        <label>LLM Model <input v-model="settings.llm_model" placeholder="qwen-plus" /></label>
        
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; margin-top: 8px;">
          <label>TTS Base URL <input v-model="settings.tts_base_url" /></label>
          <button @click="testConnection('tts')" :disabled="testStates.tts.status === 'testing'" style="height: 32px; min-width: 80px;">
            {{ testStates.tts.status === 'testing' ? '测试中...' : '测试' }}
          </button>
        </div>
        <div v-if="testStates.tts.status !== 'idle'" :style="{ color: testStates.tts.status === 'success' ? '#28a745' : testStates.tts.status === 'error' ? '#dc3545' : '#666', fontSize: '12px', marginTop: '-4px', marginBottom: '4px' }">
          {{ testStates.tts.message }}
        </div>
        <label>TTS API Key <input v-model="settings.tts_api_key" type="password" /></label>
        <label>TTS Model <input v-model="settings.tts_model" /></label>
        
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; margin-top: 8px;">
          <label>ASR Base URL <input v-model="settings.asr_base_url" /></label>
          <button @click="testConnection('asr')" :disabled="testStates.asr.status === 'testing'" style="height: 32px; min-width: 80px;">
            {{ testStates.asr.status === 'testing' ? '测试中...' : '测试' }}
          </button>
        </div>
        <div v-if="testStates.asr.status !== 'idle'" :style="{ color: testStates.asr.status === 'success' ? '#28a745' : testStates.asr.status === 'error' ? '#dc3545' : '#666', fontSize: '12px', marginTop: '-4px', marginBottom: '4px' }">
          {{ testStates.asr.message }}
        </div>
        <label>ASR API Key <input v-model="settings.asr_api_key" type="password" /></label>
        <label>ASR Model <input v-model="settings.asr_model" /></label>
        
        <label style="margin-top: 8px;">Qdrant URL <input v-model="settings.qdrant_url" /></label>
        <label>Qdrant API Key <input v-model="settings.qdrant_api_key" type="password" /></label>
        <label>AppHub URL <input v-model="settings.apphub_url" /></label>
      </div>
      <div style="margin-top: 12px">
        <button @click="saveSettings">保存配置</button>
        <span class="muted" style="margin-left: 8px">{{ saveHint }}</span>
      </div>
    </div>
  </div>
</template>

