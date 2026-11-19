# 奇怪小制作（weird little builds）

不成体系、但自己用着挺顺手的小玩意儿。单文件、无构建、丢进浏览器就能跑。

## Chat.html —「月见 · 私语」

40 KB 单文件聊天界面：深色玻璃拟态 + 月见主题，手机端优先。

- **自带 API 配置**：可填任意 OpenAI 兼容的 `baseUrl`（默认 `https://api.deepseek.com/chat/completions`）+ API Key，流式输出。
- **Key 只存本地**：写 `localStorage`（`moon_api_key`），页面里没有任何硬编码密钥，换设备不会带走。
- **背景图**：可接 `waifu.im` 随机图接口换主题背景。
- **依赖**：零依赖，打开 `Chat.html` 即用；需要联网调模型 API。

```
打开 Chat.html → 填 baseUrl（默认 DeepSeek）+ API Key → 记住它 → 开始聊
```
