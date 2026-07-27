#!/usr/bin/env python3

import os
import subprocess
import time
import objc  
from objc import super as objc_super
import sys
from Cocoa import (
    NSApplication, NSStatusBar, NSMenu, NSMenuItem, NSObject,
    NSView, NSTextField, NSSlider, NSButton, NSFont,
    NSMakeRect, NSApp, NSTimer, NSImage, NSApplicationActivationPolicyAccessory
)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    HELPER = os.path.join(BASE_DIR, "smc-helper")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    HELPER = os.path.join(BASE_DIR, "helper", "smc-helper")

# Language dictionary
LANG_STRINGS = {
    "es": {
        "fan": "Ventilador",
        "auto": "Volver a modo automático",
        "quit": "Salir",
        "error": "Error leyendo SMC",
        "toggle_btn": "ES"  # Button text to switch to English
    },
    "en": {
        "fan": "Fan",
        "auto": "Return to automatic mode",
        "quit": "Quit",
        "error": "Error reading SMC",
        "toggle_btn": "EN"  # Button text to switch to Spanish
    }
}

def run_helper(args):
    r = subprocess.run([HELPER] + [str(a) for a in args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def parse_info(output):
    fans, temps = [], {"cpu": None, "gpu": None}
    for line in output.splitlines():
        if line.startswith("TEMP_CPU="):
            try: temps["cpu"] = float(line.split("=", 1)[1])
            except: pass
        elif line.startswith("TEMP_GPU="):
            try: temps["gpu"] = float(line.split("=", 1)[1])
            except: pass
        elif line.startswith("FAN="):
            p = dict(t.split("=", 1) for t in line.split())
            fans.append({
                "index": int(p["FAN"]),
                "actual": float(p["ACTUAL"]),
                "min": float(p["MIN"]),
                "max": float(p["MAX"]),
                "mode": p["MODE"],
            })
    return fans, temps


class TempHeaderView(NSView):
    """Custom view for temperatures and the language button"""
    def initWithTarget_action_(self, target, action):
        self = objc_super(TempHeaderView, self).initWithFrame_(NSMakeRect(0, 0, 280, 30))
        if self is None:
            return None

        # Temperatures label
        self.temp_label = NSTextField.labelWithString_("CPU —   ·   GPU —")
        self.temp_label.setFrame_(NSMakeRect(16, 6, 200, 18))
        self.temp_label.setFont_(NSFont.systemFontOfSize_weight_(13, 0.0))
        self.addSubview_(self.temp_label)

        # Language button (Minimalist inline style)
        self.lang_btn = NSButton.alloc().initWithFrame_(NSMakeRect(230, 5, 38, 20))
        self.lang_btn.setBezelStyle_(15)  # NSBezelStyleInline (very clean and native)
        self.lang_btn.setTarget_(target)
        self.lang_btn.setAction_(action)
        self.addSubview_(self.lang_btn)

        return self

    @objc.python_method
    def updateTemps(self, cpu_str, gpu_str):
        self.temp_label.setStringValue_(f"CPU {cpu_str}   ·   GPU {gpu_str}")

    @objc.python_method
    def updateBtnTitle(self, text):
        self.lang_btn.setTitle_(text)


class FanSliderView(NSView):
    """Custom view containing a fan's slider"""
    def initWithFan_min_max_lang_(self, fan_index, min_rpm, max_rpm, lang_prefix):
        self = objc_super(FanSliderView, self).initWithFrame_(NSMakeRect(0, 0, 280, 70))
        if self is None:
            return None

        self.fan_index = fan_index
        self.last_user_move = 0.0

        # Title
        self.title_label = NSTextField.labelWithString_(f"{lang_prefix} {fan_index}")
        self.title_label.setFrame_(NSMakeRect(12, 42, 180, 18))
        self.title_label.setFont_(NSFont.systemFontOfSize_(12))
        self.addSubview_(self.title_label)

        # RPM Value
        self.value_label = NSTextField.labelWithString_("— RPM")
        self.value_label.setFrame_(NSMakeRect(190, 42, 80, 18))
        self.value_label.setFont_(NSFont.systemFontOfSize_(12))
        self.value_label.setAlignment_(2)  # right
        self.addSubview_(self.value_label)

        # Slider
        self.slider = NSSlider.alloc().initWithFrame_(NSMakeRect(12, 12, 200, 22))
        self.slider.setMinValue_(min_rpm)
        self.slider.setMaxValue_(max_rpm)
        self.slider.setContinuous_(True)
        self.slider.setTarget_(self)
        self.slider.setAction_("sliderChanged:")
        self.addSubview_(self.slider)

        # Apply button
        self.apply_btn = NSButton.alloc().initWithFrame_(NSMakeRect(220, 10, 50, 26))
        self.apply_btn.setTitle_("OK")
        self.apply_btn.setBezelStyle_(1)
        self.apply_btn.setTarget_(self)
        self.apply_btn.setAction_("apply:")
        self.addSubview_(self.apply_btn)

        return self

    def sliderChanged_(self, sender):
        self.last_user_move = time.time()
        val = int(sender.floatValue())
        self.value_label.setStringValue_(f"{val} RPM")

    def apply_(self, sender):
        rpm = int(self.slider.floatValue())
        run_helper(["set", self.fan_index, rpm])

    @objc.python_method
    def updateWithActual(self, actual):
        if time.time() - self.last_user_move > 3.5:
            self.slider.setFloatValue_(actual)
            self.value_label.setStringValue_(f"{int(actual)} RPM")
            
    @objc.python_method
    def updateTitle(self, title):
        self.title_label.setStringValue_(title)


class AppDelegate(NSObject):

    def applicationDidFinishLaunching_(self, notification):
        NSApp.setActivationPolicy_(1)
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self.lang = "en"  # Default language

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("fan", None)
        if image is None:
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("fan.fill", None)

        if image is not None:
            image.setTemplate_(True)
            self.status_item.button().setImage_(image)
            self.status_item.button().setTitle_("")
        else:
            self.status_item.button().setTitle_("Fan")

        self.menu = NSMenu.alloc().init()
        self.status_item.setMenu_(self.menu)

        self.fan_views = {}
        self.header_view = None
        
        # References to menu items to change text on the fly
        self.auto_item = None
        self.quit_item = None

        self.rebuild_menu()

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.5, self, "timerRefresh:", None, True
        )

    def toggleLang_(self, sender):
        """Changes the language and updates the UI without closing the menu"""
        self.lang = "en" if self.lang == "es" else "es"
        strings = LANG_STRINGS[self.lang]
        
        # Update top button
        if self.header_view:
            self.header_view.updateBtnTitle(strings["toggle_btn"])
            
        # Update fan titles
        for idx, view in self.fan_views.items():
            view.updateTitle(f"{strings['fan']} {idx}")
            
        # Update fixed menu options
        if self.auto_item:
            self.auto_item.setTitle_(strings["auto"])
        if self.quit_item:
            self.quit_item.setTitle_(strings["quit"])

    def rebuild_menu(self):
        self.menu.removeAllItems()

        code, out, _ = run_helper(["info"])
        if code != 0:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                LANG_STRINGS[self.lang]["error"], None, "")
            self.menu.addItem_(item)
            return

        fans, temps = parse_info(out)

        # Header with temperatures and language button
        self.header_view = TempHeaderView.alloc().initWithTarget_action_(self, "toggleLang:")
        self.header_view.updateBtnTitle(LANG_STRINGS[self.lang]["toggle_btn"])
        
        cpu = f"{temps['cpu']:.1f}°C" if temps["cpu"] is not None else "—"
        gpu = f"{temps['gpu']:.1f}°C" if temps["gpu"] is not None else "—"
        self.header_view.updateTemps(cpu, gpu)

        header_item = NSMenuItem.alloc().init()
        header_item.setView_(self.header_view)
        self.menu.addItem_(header_item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # One slider per fan
        for fan in fans:
            idx = fan["index"]
            mn = fan["min"] if fan["min"] < fan["max"] else 2000
            mx = fan["max"] if fan["max"] > fan["min"] else 7000

            view = FanSliderView.alloc().initWithFan_min_max_lang_(
                idx, mn, mx, LANG_STRINGS[self.lang]["fan"]
            )
            view.updateWithActual(fan["actual"])

            item = NSMenuItem.alloc().init()
            item.setView_(view)
            self.menu.addItem_(item)

            self.fan_views[idx] = view

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Automatic mode
        self.auto_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            LANG_STRINGS[self.lang]["auto"], "setAuto:", "")
        self.auto_item.setTarget_(self)
        self.menu.addItem_(self.auto_item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Quit
        self.quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            LANG_STRINGS[self.lang]["quit"], "terminate:", "q")
        self.menu.addItem_(self.quit_item)

        # Update icon title
        if fans:
            avg = sum(f["actual"] for f in fans) / len(fans)
            self.status_item.button().setTitle_(f" {int(avg)}")

    def timerRefresh_(self, timer):
        code, out, _ = run_helper(["info"])
        if code != 0:
            return

        fans, temps = parse_info(out)

        # Update temperatures text in custom view
        if self.header_view:
            cpu = f"{temps['cpu']:.1f}°C" if temps["cpu"] is not None else "—"
            gpu = f"{temps['gpu']:.1f}°C" if temps["gpu"] is not None else "—"
            self.header_view.updateTemps(cpu, gpu)

        for fan in fans:
            idx = fan["index"]
            if idx in self.fan_views:
                self.fan_views[idx].updateWithActual(fan["actual"])

        if fans:
            avg = sum(f["actual"] for f in fans) / len(fans)
            self.status_item.button().setTitle_(f" {int(avg)}")

    def setAuto_(self, sender):
        run_helper(["auto"])
        self.rebuild_menu()

def main():
    if not os.path.exists(HELPER):
        print(" smc-helper not found")
        return

    st = os.stat(HELPER)
    if not (st.st_mode & 0o4000) or st.st_uid != 0:
        print("  The helper is not setuid root.")
        print("Run this once:")
        print(f"  sudo chown root:wheel {HELPER}")
        print(f"  sudo chmod 4755 {HELPER}")
        return

    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()

if __name__ == "__main__":
    main()