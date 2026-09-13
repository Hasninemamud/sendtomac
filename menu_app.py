"""Menu-bar shell for the Mac app. The share page stays the same."""

from __future__ import annotations

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSEventModifierFlagControl,
    NSEventTypeRightMouseUp,
    NSImage,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSView,
    NSViewController,
    NSViewHeightSizable,
    NSViewWidthSizable,
)
from Foundation import NSDistributedNotificationCenter, NSObject, NSTimer, NSURL, NSURLRequest
from WebKit import WKWebView, WKWebViewConfiguration

SHOW_NOTE = "app.sendtomac.show"
POPOVER_SIZE = (380, 560)


class OpenPanelDelegate(NSObject):
    def webView_runOpenPanelWithParameters_initiatedByFrame_completionHandler_(
        self, _web, parameters, _frame, handler
    ):
        from AppKit import NSOpenPanel

        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(bool(parameters.allowsMultipleSelection()))
        if panel.runModal() == 1:
            handler(panel.URLs())
        else:
            handler(None)


class ShareController(NSViewController):
    def initWithURL_(self, url):
        self = objc.super(ShareController, self).init()
        if self is None:
            return None
        self.url = url
        self.picker = OpenPanelDelegate.alloc().init()
        frame = NSMakeRect(0, 0, POPOVER_SIZE[0], POPOVER_SIZE[1])
        view = NSView.alloc().initWithFrame_(frame)
        web = WKWebView.alloc().initWithFrame_configuration_(frame, WKWebViewConfiguration.alloc().init())
        web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        web.setUIDelegate_(self.picker)
        web.loadRequest_(NSURLRequest.requestWithURL_(NSURL.URLWithString_(url)))
        view.addSubview_(web)
        self.setView_(view)
        self.setPreferredContentSize_(POPOVER_SIZE)
        return self


class MenuApp(NSObject):
    def initWithServer_(self, start_server):
        self = objc.super(MenuApp, self).init()
        if self is None:
            return None
        self.start_server = start_server
        self.httpd = None
        self.status = None
        self.popover = None
        self.page = None
        self.url = None
        return self

    def applicationDidFinishLaunching_(self, _notification):
        self.install_status()
        self.httpd, port = self.start_server()
        self.url = f"http://127.0.0.1:{port}/share?app=1"
        NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "showFromNote:", SHOW_NOTE, None
        )
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.15, self, "showPopover:", None, False
        )

    def applicationWillTerminate_(self, _notification):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()

    def install_status(self):
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("laptopcomputer", "SendToMac")
        if image is None:
            image = NSImage.alloc().init()
        image.setTemplate_(True)
        item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = item.button()
        button.setImage_(image)
        button.setToolTip_("SendToMac")
        button.setTarget_(self)
        button.setAction_("toggle:")
        menu = NSMenu.alloc().init()
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Open", "showPopover:", "")
        open_item.setTarget_(self)
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit SendToMac", "quit:", "q")
        quit_item.setTarget_(self)
        menu.addItem_(open_item)
        menu.addItem_(quit_item)
        self.menu = menu
        self.status = item

    def toggle_(self, _sender):
        event = NSApplication.sharedApplication().currentEvent()
        flags = event.modifierFlags() if event is not None else 0
        if event is not None and (event.type() == NSEventTypeRightMouseUp or flags & NSEventModifierFlagControl):
            self.status.popUpStatusItemMenu_(self.menu)
            return
        if self.popover is not None and self.popover.isShown():
            self.popover.performClose_(None)
            return
        self.showPopover_(None)

    def showFromNote_(self, _notification):
        self.performSelectorOnMainThread_withObject_waitUntilDone_("showPopover:", None, False)

    def showPopover_(self, _sender):
        if not self.url or self.status is None:
            return
        if self.popover is None:
            page = ShareController.alloc().initWithURL_(self.url)
            pop = NSPopover.alloc().init()
            pop.setBehavior_(NSPopoverBehaviorTransient)
            pop.setAnimates_(True)
            pop.setContentSize_(POPOVER_SIZE)
            pop.setContentViewController_(page)
            self.page = page
            self.popover = pop
        button = self.status.button()
        self.popover.showRelativeToRect_ofView_preferredEdge_(button.bounds(), button, 1)

    def quit_(self, _sender):
        NSApplication.sharedApplication().terminate_(None)


def signal_running() -> None:
    NSDistributedNotificationCenter.defaultCenter().postNotificationName_object_userInfo_deliverImmediately_(
        SHOW_NOTE, None, None, True
    )


def run_menu_app(start_server) -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = MenuApp.alloc().initWithServer_(start_server)
    app.setDelegate_(delegate)
    app.run()
