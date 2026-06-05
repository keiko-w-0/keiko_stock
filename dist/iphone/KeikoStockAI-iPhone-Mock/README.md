# Keiko Stock AI iPhone Mock Shell

当前目录是 iPhone mock app 的 SwiftUI/WKWebView 壳。它加载 `Web/index.html`，先使用前端内置 mock 数据，不依赖 Mac 本地 FastAPI。

由于当前机器只有 Command Line Tools，没有完整 Xcode、iOS SDK、模拟器和签名环境，这里不能直接生成 `.ipa`。使用方式：

1. 在安装完整 Xcode 的 Mac 上，新建 iOS App 项目，Product Name 填 `KeikoStockAI`。
2. 把 `App/` 内的 Swift 文件加入项目 target。
3. 把 `Web/` 文件夹以 folder reference 方式加入 target，确保资源会被复制到 app bundle。
4. 设置 Team / Bundle Identifier。
5. 连接 iPhone 后运行，或 Archive 后用 Apple Developer 账号签名分发。

真实版本建议让 iPhone 访问云端 API，而不是直接访问 Mac 本机 SQLite。
