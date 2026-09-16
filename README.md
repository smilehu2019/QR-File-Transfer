# QR File Transfer

专为堡垒机、跳板机等物理隔离或网络受限环境（如 SecureCRT / SSH 纯终端环境）设计的轻量级文件外发工具。

## 工作原理

1. **发送端 (`qr_display.py`)**：
   * 计算原始文件 SHA256 并使用 Gzip 最高压缩率压缩。
   * 转换为 Base64 并按指定步长分片（默认 1200 字节）。
   * 拼装自定义协议头（`QRF1`），通过 `qrencode` 渲染为 ANSI-UTF8 字符二维码逐屏展示。

2. **接收端 (`qr_import.py`)**：
   * 支持通过文本流或直接扫描图片目录（依赖 `zbarimg`）批量录入分片数据。
   * 具备传输 ID 过滤、重复片剔除与分片缺失检测。
   * 自动按序号拼装、Base64 解码、Gzip 解压并比对 SHA256 完整性哈希。

## 依赖环境

* **Python**: 2.7 / 3.x 兼容设计
* **发送端系统依赖**: `qrencode` (`yum install qrencode` 或 `apt install qrencode`)
* **接收端系统依赖**: `zbar` / `zbarimg`（如果使用图片扫描模式）

## 使用方法

### 1. 发送端展示二维码
```bash
python qr_display.py <要传输的文件>
# 敲击 Enter 键逐页轮播二维码并使用手机/相机拍照记录
