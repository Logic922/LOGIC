# gRPC 模式（7859）详情 —— 目前不可用于出图，仅备查

Draw Things 的「协议 = gRPC」时，服务在 **7859**，走 HTTP/2 + TLS（自签证书）。

## 实测

```bash
# 非 gRPC 请求会得到 415
curl -sk -m 4 -D- https://127.0.0.1:7859/            # HTTP/2 415
curl -sk --http2-prior-knowledge -D- https://127.0.0.1:7859/   # 同样 415
```

服务名（无 package）：`ImageGenerationService`

```bash
printf '\x00\x00\x00\x00\x00' > /tmp/f.bin     # 空 gRPC 帧
curl -sk --http2-prior-knowledge -X POST https://127.0.0.1:7859/ImageGenerationService/Echo \
  -H 'content-type: application/grpc' -H 'te: trailers' --data-binary @/tmp/f.bin
# → grpc-status: 0，body 里 "HELLO"，且不需要 sharedSecret
```

方法（来自 upstream `imageService.proto`）：

```
rpc GenerateImage(ImageGenerationRequest) returns (stream ImageGenerationResponse);
rpc FilesExist / UploadFile / Echo / Pubkey / Hours
```

## 为什么不能直接用

`ImageGenerationRequest.configuration` 是 **FlatBuffer** 字节（不是 protobuf），字段：
`prompt(5)` `negativePrompt(6)` `configuration(7)` `scaleFactor(2)` `chunked(14)` `sharedSecret(13)`。
构造它需要 draw-things 的 `config.fbs` + `flatc` 编译，iSH(aarch64 musl) 没有现成 flatc 二进制。
gRPC 反射也被关掉（`ServerReflectionInfo` 返回 `is not implemented`），无法自动枚举方法。

结论：**要出图就用 HTTP 模式（7860）**，gRPC 只在需要 Echo 健康检查时有意义。

## 不要踩的坑

- `grpc-status: 12 / is not implemented` = 方法路径写错了，不是服务没开。
- 方法名带 `drawthings.v2.` 前缀的各种猜测全部失败，正确形态是无包名的 `ImageGenerationService`。
