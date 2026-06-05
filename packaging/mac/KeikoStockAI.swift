import Cocoa
import Foundation
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var serverProcess: Process?
    private let port = 8123

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        startBackend()
        createWindow()
        waitForBackend(attempt: 0)
    }

    func applicationWillTerminate(_ notification: Notification) {
        serverProcess?.terminate()
    }

    private func createWindow() {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        self.webView = webView

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1220, height: 860),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Keiko Stock AI"
        window.minSize = NSSize(width: 1040, height: 720)
        window.contentView = webView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = window
    }

    private func startBackend() {
        guard let appRoot = Bundle.main.resourceURL?.appendingPathComponent("app") else {
            showStartupError("找不到打包资源目录。")
            return
        }

        let supportDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Keiko Stock AI", isDirectory: true)
        let dataDir = supportDir.appendingPathComponent("data", isDirectory: true)
        let logDir = supportDir.appendingPathComponent("logs", isDirectory: true)
        try? FileManager.default.createDirectory(at: dataDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

        let process = Process()
        process.executableURL = pythonExecutable()
        process.currentDirectoryURL = appRoot
        process.arguments = [
            "-B", "-m", "uvicorn", "backend.app:app",
            "--host", "127.0.0.1",
            "--port", "\(port)"
        ]

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = appRoot.path
        environment["KEIKO_DATA_DIR"] = dataDir.path
        environment["PATH"] = [
            "/opt/homebrew/Caskroom/miniconda/base/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin"
        ].joined(separator: ":")
        process.environment = environment

        let logURL = logDir.appendingPathComponent("server.log")
        FileManager.default.createFile(atPath: logURL.path, contents: nil)
        if let handle = try? FileHandle(forWritingTo: logURL) {
            handle.seekToEndOfFile()
            process.standardOutput = handle
            process.standardError = handle
        }

        do {
            try process.run()
            serverProcess = process
        } catch {
            showStartupError("后端启动失败：\(error.localizedDescription)\n日志：\(logURL.path)")
        }
    }

    private func waitForBackend(attempt: Int) {
        guard attempt < 80 else {
            showStartupError("后端启动超时。请确认 Python 已安装依赖：pip install -r requirements.txt")
            return
        }

        let url = URL(string: "http://127.0.0.1:\(port)/api/health")!
        URLSession.shared.dataTask(with: url) { _, response, _ in
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            DispatchQueue.main.async {
                if ok {
                    self.webView?.load(URLRequest(url: URL(string: "http://127.0.0.1:\(self.port)/")!))
                } else {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                        self.waitForBackend(attempt: attempt + 1)
                    }
                }
            }
        }.resume()
    }

    private func pythonExecutable() -> URL {
        let candidates = [
            "/opt/homebrew/Caskroom/miniconda/base/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for candidate in candidates where FileManager.default.isExecutableFile(atPath: candidate) {
            return URL(fileURLWithPath: candidate)
        }
        return URL(fileURLWithPath: "/usr/bin/python3")
    }

    private func showStartupError(_ message: String) {
        let alert = NSAlert()
        alert.alertStyle = .critical
        alert.messageText = "Keiko Stock AI 启动失败"
        alert.informativeText = message
        alert.runModal()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
