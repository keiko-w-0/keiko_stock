#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

@interface AppDelegate : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *webView;
@property(nonatomic, strong) NSTask *serverTask;
@property(nonatomic, assign) NSInteger port;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    self.port = 8123;
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    [self startBackend];
    [self createWindow];
    [self waitForBackend:0];
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    if (self.serverTask && self.serverTask.isRunning) {
        [self.serverTask terminate];
    }
}

- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)flag {
    if (!flag) {
        if (!self.window) {
            [self createWindow];
            [self waitForBackend:0];
        } else {
            [self.window makeKeyAndOrderFront:nil];
        }
        [NSApp activateIgnoringOtherApps:YES];
    }
    return YES;
}

- (void)createWindow {
    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    configuration.websiteDataStore = [WKWebsiteDataStore defaultDataStore];
    self.webView = [[WKWebView alloc] initWithFrame:NSZeroRect configuration:configuration];

    self.window = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(0, 0, 1220, 860)
                  styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    self.window.title = @"Keiko Stock AI";
    self.window.minSize = NSMakeSize(1040, 720);
    self.window.contentView = self.webView;
    [self.window center];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)startBackend {
    if ([self backendIsHealthy]) {
        return;
    }
    self.port = [self availablePortStartingAt:self.port];

    NSString *resourcesPath = [[NSBundle mainBundle] resourcePath];
    NSString *appRoot = [resourcesPath stringByAppendingPathComponent:@"app"];

    NSFileManager *fm = [NSFileManager defaultManager];
    NSURL *supportURL = [[fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject
        URLByAppendingPathComponent:@"Keiko Stock AI" isDirectory:YES];
    NSURL *dataURL = [supportURL URLByAppendingPathComponent:@"data" isDirectory:YES];
    NSURL *logURL = [supportURL URLByAppendingPathComponent:@"logs" isDirectory:YES];
    [fm createDirectoryAtURL:dataURL withIntermediateDirectories:YES attributes:nil error:nil];
    [fm createDirectoryAtURL:logURL withIntermediateDirectories:YES attributes:nil error:nil];

    NSString *serverLog = [[logURL path] stringByAppendingPathComponent:@"server.log"];
    [fm createFileAtPath:serverLog contents:nil attributes:nil];
    NSFileHandle *logHandle = [NSFileHandle fileHandleForWritingAtPath:serverLog];
    [logHandle seekToEndOfFile];

    NSTask *task = [[NSTask alloc] init];
    task.launchPath = [self pythonExecutable];
    task.currentDirectoryPath = appRoot;
    task.arguments = @[
        @"-B", @"-m", @"uvicorn", @"backend.app:app",
        @"--host", @"127.0.0.1",
        @"--port", [NSString stringWithFormat:@"%ld", (long)self.port]
    ];

    NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
    environment[@"PYTHONPATH"] = appRoot;
    environment[@"KEIKO_DATA_DIR"] = [dataURL path];
    environment[@"PATH"] = @"/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin";
    task.environment = environment;
    task.standardOutput = logHandle;
    task.standardError = logHandle;

    @try {
        [task launch];
        self.serverTask = task;
    } @catch (NSException *exception) {
        [self showStartupError:[NSString stringWithFormat:@"后端启动失败：%@\n日志：%@", exception.reason, serverLog]];
    }
}

- (BOOL)backendIsHealthy {
    NSString *healthURL = [NSString stringWithFormat:@"http://127.0.0.1:%ld/api/health", (long)self.port];
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:healthURL]];
    request.timeoutInterval = 0.35;

    dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
    __block BOOL healthy = NO;
    NSURLSessionDataTask *task = [[NSURLSession sharedSession]
        dataTaskWithRequest:request
          completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
              NSInteger statusCode = [(NSHTTPURLResponse *)response statusCode];
              healthy = (statusCode == 200);
              dispatch_semaphore_signal(semaphore);
          }];
    [task resume];
    dispatch_semaphore_wait(semaphore, dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.45 * NSEC_PER_SEC)));
    [task cancel];
    return healthy;
}

- (NSInteger)availablePortStartingAt:(NSInteger)startPort {
    for (NSInteger candidate = startPort; candidate < startPort + 40; candidate++) {
        int socketFD = socket(AF_INET, SOCK_STREAM, 0);
        if (socketFD < 0) {
            continue;
        }

        int opt = 1;
        setsockopt(socketFD, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in address;
        memset(&address, 0, sizeof(address));
        address.sin_family = AF_INET;
        address.sin_port = htons((uint16_t)candidate);
        inet_pton(AF_INET, "127.0.0.1", &address.sin_addr);

        int result = bind(socketFD, (struct sockaddr *)&address, sizeof(address));
        close(socketFD);
        if (result == 0) {
            return candidate;
        }
    }
    return startPort + 100;
}

- (void)waitForBackend:(NSInteger)attempt {
    if (attempt >= 80) {
        [self showStartupError:@"后端启动超时。请确认 Python 已安装依赖：pip install -r requirements.txt"];
        return;
    }

    NSString *healthURL = [NSString stringWithFormat:@"http://127.0.0.1:%ld/api/health", (long)self.port];
    NSURLSessionDataTask *task = [[NSURLSession sharedSession]
        dataTaskWithURL:[NSURL URLWithString:healthURL]
      completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
          NSInteger statusCode = [(NSHTTPURLResponse *)response statusCode];
          dispatch_async(dispatch_get_main_queue(), ^{
              if (statusCode == 200) {
                  NSString *appURL = [NSString stringWithFormat:@"http://127.0.0.1:%ld/", (long)self.port];
                  [self.webView loadRequest:[NSURLRequest requestWithURL:[NSURL URLWithString:appURL]]];
              } else {
                  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.25 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
                      [self waitForBackend:(attempt + 1)];
                  });
              }
          });
      }];
    [task resume];
}

- (NSString *)pythonExecutable {
    NSArray<NSString *> *candidates = @[
        @"/opt/homebrew/Caskroom/miniconda/base/bin/python3",
        @"/opt/homebrew/bin/python3",
        @"/usr/local/bin/python3",
        @"/usr/bin/python3"
    ];
    NSFileManager *fm = [NSFileManager defaultManager];
    for (NSString *candidate in candidates) {
        if ([fm isExecutableFileAtPath:candidate]) {
            return candidate;
        }
    }
    return @"/usr/bin/python3";
}

- (void)showStartupError:(NSString *)message {
    NSAlert *alert = [[NSAlert alloc] init];
    alert.alertStyle = NSAlertStyleCritical;
    alert.messageText = @"Keiko Stock AI 启动失败";
    alert.informativeText = message;
    [alert runModal];
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}
