##
##  GPL License
##
##  Blender Addon | Aqueduct asset manager integration addon
##  Copyright (C) 2020  Johannes Rauch
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
        "name": "Aqueduct asset manager integration",
        "author": "Johannes Rauch",
        "version": (0, 1),
        "blender": (2, 80, 3),
        "description": "Interoperability addon for Aqueduct",
        "category": "Utility",
        }

import bpy

# submodules
from . import ad_utils

from . import ad_ops_utility
from . import ad_ops_import
from . import ad_ops_export
from . import ad_ops_filelist
from . import ad_ops_tools

from . import ad_gui

# reload all custom modules
import importlib
if "bpy" in locals():
    ad_utils.log("[INIT] Reloading submodules")

    importlib.reload(ad_utils)

    importlib.reload(ad_ops_utility)
    importlib.reload(ad_ops_import)
    importlib.reload(ad_ops_export)
    importlib.reload(ad_ops_filelist)
    importlib.reload(ad_ops_tools)

    importlib.reload(ad_gui)

addon_keymaps = []

def register():
    # unregistering the current operator for blend-file drop event
    if hasattr(bpy.types, 'WM_OT_drop_blend_file'):
        bpy.utils.unregister_class(bpy.types.WM_OT_drop_blend_file)


    # Submodules
    ad_gui.register()

    ad_ops_utility.register()
    ad_ops_import.register()
    ad_ops_export.register()
    ad_ops_filelist.register()
    ad_ops_tools.register()


    # hotkeys
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Object Mode')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'A', 'PRESS', shift=True, ctrl=True)
        kmi.properties.name = "VIEW3D_MT_PIE_Aqueduct"
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new('ad.material_quickapply', 'Q', 'PRESS', shift=True, ctrl=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new('ad.object_quickplace', 'W', 'PRESS', shift=True, ctrl=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new('ad.object_quickrotate', 'E', 'PRESS', shift=True, ctrl=True)
        addon_keymaps.append((km, kmi))

def unregister():

    # Submodules
    ad_gui.unregister()

    ad_ops_utility.unregister()
    ad_ops_import.unregister()
    ad_ops_export.unregister()
    ad_ops_filelist.unregister()
    ad_ops_tools.unregister()


    # hotkeys
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()
