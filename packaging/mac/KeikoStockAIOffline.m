#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface AppDelegate : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *webView;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    [self createWindowIfNeeded];
    [self loadBundledApp];
}

- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)flag {
    if (!flag) {
        [self createWindowIfNeeded];
        [self loadBundledApp];
        [NSApp activateIgnoringOtherApps:YES];
    }
    return YES;
}

- (void)createWindowIfNeeded {
    if (self.window) {
        [self.window makeKeyAndOrderFront:nil];
        return;
    }

    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    configuration.websiteDataStore = [WKWebsiteDataStore defaultDataStore];
    self.webView = [[WKWebView alloc] initWithFrame:NSZeroRect configuration:configuration];

    self.window = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(0, 0, 1220, 860)
                  styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    self.window.title = @"Keiko Stock AI";
    self.window.minSize = NSMakeSize(980, 680);
    self.window.contentView = self.webView;
    [self.window center];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)loadBundledApp {
    NSURL *appRoot = [[[NSBundle mainBundle] resourceURL] URLByAppendingPathComponent:@"app" isDirectory:YES];
    NSURL *indexURL = [appRoot URLByAppendingPathComponent:@"index.html"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:indexURL.path]) {
        [self.webView loadFileURL:indexURL allowingReadAccessToURL:appRoot];
    } else {
        [self.webView loadHTMLString:@"<h1>Keiko Stock AI</h1><p>Missing bundled index.html.</p>" baseURL:nil];
    }
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
