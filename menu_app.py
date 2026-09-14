"""Menu-bar shell for the Mac app. The share page stays the same."""

from __future__ import annotations

import ctypes
import json
import sys
from ctypes import CFUNCTYPE, POINTER, Structure, byref, c_int32, c_uint32, c_uint64, c_void_p
from pathlib import Path

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSDragOperationCopy,
    NSEvent,
    NSEventMaskFlagsChanged,
    NSEventMaskKeyDown,
    NSEventMaskLeftMouseUp,
    NSEventMaskRightMouseDown,
    NSEventMaskRightMouseUp,
    NSEventModifierFlagCapsLock,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagDeviceIndependentFlagsMask,
    NSEventModifierFlagOption,
    NSEventTypeRightMouseDown,
    NSEventTypeRightMouseUp,
    NSImage,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSPasteboard,
    NSPasteboardTypeFileURL,
    NSPointInRect,
    NSPopover,
    NSPopoverBehaviorSemitransient,
    NSPopoverBehaviorTransient,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSView,
    NSViewController,
    NSViewHeightSizable,
    NSViewWidthSizable,
)
from Foundation import NSBundle, NSDistributedNotificationCenter, NSObject, NSTimer, NSURL, NSURLRequest
from WebKit import WKWebView, WKWebViewConfiguration

SHOW_NOTE = "app.sendtomac.show"
POPOVER_SIZE = (560, 400)
CHORD = NSEventModifierFlagCommand | NSEventModifierFlagOption
CHORD_HOLD = 0.28
_AX = {}
_CARBON_HANDLER = None
_CARBON_REFS = []
_CG = None
_CG_OPTION = 0x00080000
_CG_COMMAND = 0x00100000
_CG_SHIFT = 0x00020000
_CG_CONTROL = 0x00040000


class _EventTypeSpec(Structure):
    _fields_ = [("eventClass", c_uint32), ("eventKind", c_uint32)]


class _EventHotKeyID(Structure):
    _fields_ = [("signature", c_uint32), ("id", c_uint32)]


def install_carbon_hotkey(callback) -> None:
    global _CARBON_HANDLER
    try:
        carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        carbon.GetApplicationEventTarget.restype = c_void_p
        carbon.GetEventDispatcherTarget.restype = c_void_p
        carbon.InstallEventHandler.argtypes = [
            c_void_p, c_void_p, c_uint32, POINTER(_EventTypeSpec), c_void_p, POINTER(c_void_p)
        ]
        carbon.InstallEventHandler.restype = c_int32
        carbon.RegisterEventHotKey.argtypes = [
            c_uint32, c_uint32, _EventHotKeyID, c_void_p, c_uint32, POINTER(c_void_p)
        ]
        carbon.RegisterEventHotKey.restype = c_int32

        def handler(_call, _event, _user):
            callback()
            return 0

        _CARBON_HANDLER = CFUNCTYPE(c_int32, c_void_p, c_void_p, c_void_p)(handler)
        specs = (_EventTypeSpec * 2)(
            _EventTypeSpec(0x6B657962, 5),
            _EventTypeSpec(0x6B657962, 6),
        )
        target = carbon.GetEventDispatcherTarget() or carbon.GetApplicationEventTarget()
        installed = c_void_p()
        if carbon.InstallEventHandler(target, _CARBON_HANDLER, 2, specs, None, byref(installed)) != 0:
            return
        pairs = ((0x37, 2048), (0x36, 2048), (0x3A, 256), (0x3D, 256))
        for index, (key, mods) in enumerate(pairs, 1):
            ref = c_void_p()
            if carbon.RegisterEventHotKey(key, mods, _EventHotKeyID(0x53544D43, index), target, 0, byref(ref)) == 0:
                _CARBON_REFS.append(ref)
    except Exception:
        return


def chord_flags_down() -> bool:
    global _CG
    if _CG is None:
        try:
            cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
            cg.CGEventSourceFlagsState.argtypes = [c_int32]
            cg.CGEventSourceFlagsState.restype = c_uint64
            _CG = cg
        except Exception:
            _CG = False
    if not _CG:
        return False
    flags = _CG.CGEventSourceFlagsState(1) & (_CG_OPTION | _CG_COMMAND | _CG_SHIFT | _CG_CONTROL)
    return flags == (_CG_OPTION | _CG_COMMAND)


def accessibility_ok(prompt=False):
    if "AXIsProcessTrustedWithOptions" not in _AX:
        try:
            bundle = NSBundle.bundleWithPath_(
                "/System/Library/Frameworks/ApplicationServices.framework"
            )
            if bundle is not None:
                bundle.load()
            objc.loadBundleFunctions(
                bundle,
                _AX,
                [
                    ("AXIsProcessTrusted", b"Z"),
                    ("AXIsProcessTrustedWithOptions", b"Z@"),
                ],
            )
        except Exception:
            return False
    check = _AX.get("AXIsProcessTrustedWithOptions")
    if check is None:
        return False
    try:
        if prompt:
            return bool(check({"AXTrustedCheckOptionPrompt": True}))
        trusted = _AX.get("AXIsProcessTrusted")
        return bool(trusted() if trusted else check(None))
    except Exception:
        return False


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


class DropOverlay(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(DropOverlay, self).initWithFrame_(frame)
        if self is None:
            return None
        self.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.registerForDraggedTypes_([NSPasteboardTypeFileURL, "NSFilenamesPboardType"])
        self.web = None
        return self

    def hitTest_(self, point):
        if not file_drag_active():
            return None
        local = self.convertPoint_fromView_(point, self.superview())
        if not NSPointInRect(local, self.bounds()):
            return None
        return self

    def draggingEntered_(self, _sender):
        self._set_over(True)
        return NSDragOperationCopy

    def draggingUpdated_(self, _sender):
        return NSDragOperationCopy

    def draggingExited_(self, _sender):
        self._set_over(False)

    def prepareForDragOperation_(self, _sender):
        return True

    def performDragOperation_(self, sender):
        self._set_over(False)
        paths = dropped_paths(sender)
        if not paths or self.web is None:
            return False
        stage_into(self.web, paths)
        return True

    def _set_over(self, on):
        if self.web is None:
            return
        flag = "true" if on else "false"
        self.web.evaluateJavaScript_completionHandler_(
            "document.getElementById('dropzone')&&document.getElementById('dropzone').classList.toggle('over'," + flag + ")",
            None,
        )


def quit_menu():
    menu = NSMenu.alloc().init()
    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit SendToMac", "quit:", "")
    item.setTarget_(NSApplication.sharedApplication().delegate())
    menu.addItem_(item)
    return menu


def file_drag_active():
    board = NSPasteboard.pasteboardWithName_("NSDragPboard")
    if board is None:
        return False
    types = list(board.types() or [])
    return NSPasteboardTypeFileURL in types or "NSFilenamesPboardType" in types


class DropWebView(WKWebView):
    def initWithFrame_configuration_(self, frame, config):
        self = objc.super(DropWebView, self).initWithFrame_configuration_(frame, config)
        if self is None:
            return None
        self.registerForDraggedTypes_([NSPasteboardTypeFileURL, "NSFilenamesPboardType"])
        return self

    def menuForEvent_(self, _event):
        return quit_menu()

    def draggingEntered_(self, _sender):
        return NSDragOperationCopy

    def draggingUpdated_(self, _sender):
        return NSDragOperationCopy

    def prepareForDragOperation_(self, _sender):
        return True

    def performDragOperation_(self, sender):
        paths = dropped_paths(sender)
        if not paths:
            return False
        self.window().makeKeyAndOrderFront_(None) if self.window() else None
        stage_into(self, paths)
        return True


def dropped_paths(sender):
    board = sender.draggingPasteboard()
    urls = board.readObjectsForClasses_options_([NSURL], None) or []
    paths = [url.path() for url in urls if url.isFileURL()]
    if paths:
        return paths
    names = board.propertyListForType_("NSFilenamesPboardType") or []
    return list(names)


class NavDelegate(NSObject):
    def webView_decidePolicyForNavigationAction_decisionHandler_(self, web, action, handler):
        url = action.request().URL()
        if url is not None and url.isFileURL() and url.path():
            handler(0)
            stage_into(web, [url.path()])
            return
        handler(1)


def stage_into(web, paths):
    from staging import stage_local

    parts = []
    for raw in paths:
        path = Path(raw)
        try:
            token = stage_local(path)
        except ValueError:
            continue
        parts.append("addStaged(" + json.dumps(token) + "," + json.dumps(path.name) + ")")
    if parts:
        web.evaluateJavaScript_completionHandler_(";".join(parts), None)


class ShareController(NSViewController):
    def initWithURL_(self, url):
        self = objc.super(ShareController, self).init()
        if self is None:
            return None
        self.url = url
        self.picker = OpenPanelDelegate.alloc().init()
        self.nav = NavDelegate.alloc().init()
        frame = NSMakeRect(0, 0, POPOVER_SIZE[0], POPOVER_SIZE[1])
        view = NSView.alloc().initWithFrame_(frame)
        web = DropWebView.alloc().initWithFrame_configuration_(frame, WKWebViewConfiguration.alloc().init())
        web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        web.setUIDelegate_(self.picker)
        web.setNavigationDelegate_(self.nav)
        overlay = DropOverlay.alloc().initWithFrame_(frame)
        overlay.web = web
        web.loadRequest_(NSURLRequest.requestWithURL_(NSURL.URLWithString_(url)))
        view.addSubview_(web)
        view.addSubview_(overlay)
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
        self.hotkey_timer = None
        self.chord_timer = None
        self.chord_used = False
        self.chord_latched = False
        self.shortcut_monitors = []
        self.shortcut_on = False
        return self

    def applicationDidFinishLaunching_(self, _notification):
        self.install_status()
        started = self.start_server()
        self.httpd = started[0]
        port = started[1]
        local_key = started[2] if len(started) > 2 else ""
        self.url = f"http://127.0.0.1:{port}/share?app=1"
        if local_key:
            self.url += f"&k={local_key}"
        NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "showFromNote:", SHOW_NOTE, None
        )
        NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "appearanceChanged:", "AppleInterfaceThemeChangedNotification", None
        )
        self.install_shortcut()
        self.register_login()
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.15, self, "showPopover:", None, False
        )

    def applicationWillTerminate_(self, _notification):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()

    def menu_is_dark(self):
        try:
            match = NSApplication.sharedApplication().effectiveAppearance().bestMatchFromAppearancesWithNames_((
                "NSAppearanceNameAqua",
                "NSAppearanceNameDarkAqua",
            ))
            return match == "NSAppearanceNameDarkAqua"
        except Exception:
            return False

    def appearanceChanged_(self, _notification):
        if self.status is None:
            return
        button = self.status.button()
        if button is not None:
            button.setImage_(self.status_image())

    def status_image(self):
        roots = []
        if getattr(sys, "frozen", False):
            roots.append(Path(sys.executable).resolve().parent.parent / "Resources" / "web")
        roots.append(Path(__file__).resolve().parent / "web")
        name = "menu-icon.png"
        for root in roots:
            path = root / name
            if path.is_file():
                image = NSImage.alloc().initWithContentsOfFile_(str(path))
                if image is not None:
                    image.setTemplate_(True)
                    image.setSize_((18, 18))
                    return image
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("laptopcomputer", "SendToMac")
        if image is None:
            image = NSImage.alloc().init()
        image.setTemplate_(True)
        return image

    def install_status(self):
        image = self.status_image()
        item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = item.button()
        button.setImage_(image)
        button.setToolTip_("SendToMac. Right-click to quit.")
        button.setTarget_(self)
        button.setAction_("toggle:")
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)
        menu = NSMenu.alloc().init()
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Open", "showPopover:", "")
        open_item.setTarget_(self)
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit SendToMac", "quit:", "q")
        quit_item.setTarget_(self)
        menu.addItem_(open_item)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(quit_item)
        self.menu = menu
        self.status = item
        local = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskRightMouseDown, self.localRightClick_
        )
        if local is not None:
            self.shortcut_monitors.append(local)

    def install_shortcut(self):
        install_carbon_hotkey(lambda: self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "openFromShortcut:", None, False
        ))
        self.attach_shortcut()
        self.chord_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, "pollChord:", None, True
        )
        self.register_login()
        if not accessibility_ok(prompt=False):
            accessibility_ok(prompt=True)

    def register_login(self):
        if not getattr(sys, "frozen", False):
            return
        try:
            bundle = NSBundle.bundleWithPath_("/System/Library/Frameworks/ServiceManagement.framework")
            if bundle is None or not bundle.load():
                return
            service = objc.lookUpClass("SMAppService").mainAppService()
            if int(service.status()) == 1:
                return
            service.registerAndReturnError_(None)
        except Exception:
            return

    def openFromShortcut_(self, _sender):
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, "showPopover:", None, False
        )

    def attach_shortcut(self):
        if self.shortcut_on:
            return
        self.shortcut_on = True
        handlers = (
            (NSEventMaskFlagsChanged, self.flagsChanged_, self.localFlagsChanged_),
            (NSEventMaskKeyDown, self.cancelHotkey_, self.localKeyDown_),
        )
        for mask, global_handler, local_handler in handlers:
            watched = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, global_handler)
            local = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(mask, local_handler)
            if watched is not None:
                self.shortcut_monitors.append(watched)
            if local is not None:
                self.shortcut_monitors.append(local)

    def chord_down(self, event=None):
        raw = event.modifierFlags() if event is not None else NSEvent.modifierFlags()
        flags = raw & NSEventModifierFlagDeviceIndependentFlagsMask
        flags &= ~NSEventModifierFlagCapsLock
        return flags == CHORD

    def pollChord_(self, _timer):
        down = chord_flags_down()
        if down and not self.chord_latched:
            self.chord_latched = True
            self.showPopover_(None)
        elif not down:
            self.chord_latched = False

    def flagsChanged_(self, event):
        if self.chord_down(event):
            if self.chord_used:
                return
            self.chord_used = True
            self.openFromShortcut_(None)
        else:
            self.chord_used = False

    def localFlagsChanged_(self, event):
        self.flagsChanged_(event)
        return event

    def localKeyDown_(self, event):
        self.cancelHotkey_(None)
        return event

    def armHotkey(self):
        if self.hotkey_timer is not None:
            return
        self.chord_used = False
        self.hotkey_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            CHORD_HOLD, self, "hotkeyFired:", None, False
        )

    def cancelHotkey_(self, _event):
        self.chord_used = True
        if self.hotkey_timer is None:
            return
        self.hotkey_timer.invalidate()
        self.hotkey_timer = None

    def releaseChord(self):
        armed = self.hotkey_timer is not None
        if self.hotkey_timer is not None:
            self.hotkey_timer.invalidate()
            self.hotkey_timer = None
        if armed and not self.chord_used:
            self.showPopover_(None)
        self.chord_used = False

    def hotkeyFired_(self, _timer):
        self.hotkey_timer = None
        if self.chord_used or not self.chord_down():
            return
        self.chord_used = True
        self.showPopover_(None)

    def localRightClick_(self, event):
        if self.popover is None or not self.popover.isShown():
            return event
        page = self.popover.contentViewController()
        view = page.view() if page is not None else None
        if view is None or view.window() is None or event.window() != view.window():
            return event
        NSMenu.popUpContextMenu_withEvent_forView_(self.menu, event, view)
        return None

    def toggle_(self, _sender):
        event = NSApplication.sharedApplication().currentEvent()
        flags = event.modifierFlags() if event is not None else 0
        right = event is not None and event.type() in {NSEventTypeRightMouseUp, NSEventTypeRightMouseDown}
        if right or flags & NSEventModifierFlagControl:
            self.status.button().highlight_(False)
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
            pop.setBehavior_(NSPopoverBehaviorSemitransient)
            pop.setAnimates_(True)
            pop.setContentSize_(POPOVER_SIZE)
            pop.setContentViewController_(page)
            self.page = page
            self.popover = pop
        app = NSApplication.sharedApplication()
        try:
            app.activate()
        except Exception:
            app.activateIgnoringOtherApps_(True)
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
