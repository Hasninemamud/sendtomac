# dmgbuild settings for SendToMac (see scripts/make-dmg.sh).
import os

root = defines["ROOT"]
stage = defines["STAGE"]
app = os.path.join(stage, "SendToMac.app")

files = [app]
symlinks = {"Applications": "/Applications"}
background = os.path.join(root, "assets", "dmg-background.png")
window_rect = ((200, 120), (660, 420))
icon_size = 112.0
text_size = 16.0
icon_locations = {
    "SendToMac.app": (150, 170),
    "Applications": (510, 170),
}
hide_extensions = ["SendToMac.app"]
format = "UDZO"
filesystem = "HFS+"
