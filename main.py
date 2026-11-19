from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from color_detector import ColorDetector
from macro_engine import MacroEngine, MacroStep
from storage import MacroStore

KV = r"""
<RootUI>:
    orientation: "vertical"
    padding: "12dp"
    spacing: "9dp"
    canvas.before:
        Color:
            rgba: 0.025, 0.025, 0.035, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        size_hint_y: None
        height: "52dp"
        Label:
            text: "[b]CART3R // MACRO CORE[/b]"
            markup: True
            color: 1, 0.18, 0.28, 1
            font_size: "19sp"
            halign: "left"
        Label:
            text: "ANDROID BUILD 0.2"
            color: .65, .65, .7, 1
            font_size: "10sp"
            size_hint_x: .45
    Label:
        text: root.status
        size_hint_y: None
        height: "34dp"
        color: .9, .75, .78, 1
    TabbedPanel:
        do_default_tab: False
        TabbedPanelItem:
            text: "COLOR"
            BoxLayout:
                orientation: "vertical"
                padding: "8dp"
                spacing: "8dp"
                Camera:
                    id: camera
                    resolution: (640, 480)
                    play: True
                BoxLayout:
                    size_hint_y: None
                    height: "44dp"
                    spacing: "6dp"
                    Button:
                        text: "Start scan"
                        on_release: root.start_scan()
                    Button:
                        text: "Stop scan"
                        on_release: root.stop_scan()
                Label:
                    id: color_result
                    text: "Camera color scan is stopped"
                    color: 1, 1, 1, 1
                    size_hint_y: None
                    height: "48dp"
                Label:
                    text: "Default target: red. Detection uses sampled camera pixels."
                    color: .65, .65, .7, 1
                    font_size: "11sp"
                    size_hint_y: None
                    height: "30dp"
        TabbedPanelItem:
            text: "MACROS"
            BoxLayout:
                orientation: "vertical"
                padding: "8dp"
                spacing: "8dp"
                TextInput:
                    id: macro_name
                    hint_text: "Macro name"
                    multiline: False
                    size_hint_y: None
                    height: "44dp"
                Spinner:
                    id: action_type
                    text: "wait"
                    values: ["wait", "tap", "swipe", "note"]
                    size_hint_y: None
                    height: "44dp"
                TextInput:
                    id: action_args
                    hint_text: "wait: seconds | tap: x,y (0..1) | swipe: x1,y1,x2,y2,duration"
                    multiline: False
                    size_hint_y: None
                    height: "60dp"
                BoxLayout:
                    size_hint_y: None
                    height: "44dp"
                    spacing: "6dp"
                    Button:
                        text: "Add step"
                        on_release: root.add_step()
                    Button:
                        text: "Save macro"
                        on_release: root.save_macro()
                Label:
                    id: step_list
                    text: "No steps yet"
                    color: 1, 1, 1, 1
                    text_size: self.width, None
                    valign: "top"
                Button:
                    text: "Run safe preview"
                    size_hint_y: None
                    height: "48dp"
                    on_release: root.run_preview()
        TabbedPanelItem:
            text: "INFO"
            BoxLayout:
                orientation: "vertical"
                padding: "12dp"
                spacing: "10dp"
                Label:
                    text: "CART3R Macro Core 0.2"
                    color: 1, .3, .38, 1
                    size_hint_y: None
                    height: "35dp"
                Label:
                    text: "This build supports camera-based color detection, macro editing, and local JSON storage. Full-screen capture needs Android MediaProjection consent. Cross-app taps/swipes need a native AccessibilityService that the user explicitly enables. Those features are not active in this MVP."
                    color: .85, .85, .88, 1
                    text_size: self.width, None
                    halign: "left"
                    valign: "top"
"""

class RootUI(BoxLayout):
    status = StringProperty("READY // CART3R Macro Core 0.2")
    steps = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.detector = ColorDetector()
        self.engine = MacroEngine()
        self.store = MacroStore()
        self.scan_event = None

    def start_scan(self):
        self.ids.camera.play = True
        if self.scan_event:
            self.scan_event.cancel()
        self.scan_event = Clock.schedule_interval(self._scan_camera, 0.6)
        self.status = "COLOR SCAN ACTIVE"

    def stop_scan(self):
        if self.scan_event:
            self.scan_event.cancel()
            self.scan_event = None
        self.status = "COLOR SCAN STOPPED"

    def _scan_camera(self, _dt):
        texture = self.ids.camera.texture
        if not texture:
            return
        try:
            result = self.detector.detect_rgba(
                texture.pixels, texture.width, texture.height
            )
            self.ids.color_result.text = (
                f"Target pixels: {result['count']} | "
                f"Coverage: {result['coverage']:.1f}% | "
                f"Center: {result['center']}"
            )
        except Exception as exc:
            self.ids.color_result.text = f"Frame error: {exc}"

    def add_step(self):
        kind = self.ids.action_type.text
        raw = self.ids.action_args.text.strip()
        try:
            if kind == "wait":
                args = {"seconds": float(raw or "1")}
            elif kind == "tap":
                p = [float(v.strip()) for v in raw.split(",")]
                if len(p) != 2:
                    raise ValueError("tap requires x,y")
                args = {"x": p[0], "y": p[1]}
            elif kind == "swipe":
                p = [float(v.strip()) for v in raw.split(",")]
                if len(p) != 5:
                    raise ValueError("swipe requires x1,y1,x2,y2,duration")
                args = dict(zip(("x1", "y1", "x2", "y2", "duration"), p))
            else:
                args = {"text": raw}
            self.steps.append(MacroStep(kind, args).to_dict())
            self.ids.step_list.text = "\n".join(
                f"{i+1}. {s['kind']} {s['args']}" for i, s in enumerate(self.steps)
            )
            self.status = f"STEP ADDED // {kind}"
        except Exception as exc:
            self.status = f"INVALID STEP // {exc}"

    def save_macro(self):
        name = self.ids.macro_name.text.strip() or "Untitled Macro"
        self.store.save(name, self.steps)
        self.status = f"SAVED // {name}"

    def run_preview(self):
        try:
            summary = self.engine.preview(self.steps)
            Popup(title="Safe macro preview", content=Label(text=summary),
                  size_hint=(.92, .72)).open()
            self.status = "PREVIEW COMPLETE // no device actions executed"
        except Exception as exc:
            self.status = f"MACRO ERROR // {exc}"

class MacroCoreApp(App):
    def build(self):
        Builder.load_string(KV)
        return RootUI()

    def on_stop(self):
        if self.root:
            self.root.stop_scan()

if __name__ == "__main__":
    MacroCoreApp().run()
