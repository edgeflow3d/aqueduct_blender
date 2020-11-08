import os

import bpy
import bpy.utils.previews

from bpy.types import Operator, Menu, AddonPreferences, UIList, PropertyGroup
from bpy.props import StringProperty, EnumProperty, IntProperty, CollectionProperty, IntProperty

def make_path_absolute(key):
    props = bpy.context.preferences.addons[__package__].preferences
    sane_path = lambda p: os.path.abspath(bpy.path.abspath(p))

    # if key in props and props[key].startswith('//'):
    if key in props:
        props[key] = sane_path(props[key])

class AD_UL_ListItem(PropertyGroup):
    """ Propertygroup holding info for filelist items """

    mode : EnumProperty(name="Mode",
            items=[
                ('OBJECT', "Object", 'OBJECT_DATA', 0),
                ('MATERIAL', "Material", 'MATERIAL', 1)
                ],
            default='OBJECT'
            )

    filepath: StringProperty(
            name="Filepath",
            description="Path to the blendfile",
            default="")

class AD_UL_Filelist(UIList):
    """ Blendfile list"""

    def draw_item(self, context, layout ,data, item, icon, active_data,
            active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            split = row.split(factor=0.2)
            split.prop(item, "mode", text="")
            split.label(text=item.filepath)

class AD_Preferences(AddonPreferences):
    bl_idname = __package__

    # Library basepath
    AD_library_path : StringProperty(
            default="",
            subtype="DIR_PATH",
            update=lambda s,c: make_path_absolute('AD_library_path')
                )

    # Studio paths
    AD_object_studio_path : StringProperty(
            default=os.path.join(os.path.dirname(__file__), "resources", "studio_objects.blend"),
            subtype="FILE_PATH",
            update=lambda s,c: make_path_absolute('AD_object_studio_path')
                )
    AD_material_studio_path : StringProperty(
            default=os.path.join(os.path.dirname(__file__), "resources", "studio_materials.blend"),
            subtype="FILE_PATH",
            update=lambda s,c: make_path_absolute('AD_material_studio_path')
                )

    AD_thumbnail_size : IntProperty(
            name="Thumbnail size",
            default=500,
            min=150,
            max=500,
            subtype='PIXEL')

    # Recent chosen export path
    AD_export_path : StringProperty(default="")

    # Filelist props
    AD_batchrender_list : CollectionProperty(type=AD_UL_ListItem)
    AD_batchrender_list_index : IntProperty(default=0)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'AD_library_path', text="Library folder")
        row = layout.row()
        row.prop(self, 'AD_object_studio_path', text="Object Studio file")
        row = layout.row()
        row.prop(self, 'AD_material_studio_path', text="Material Studio file")
        row = layout.row()
        split = row.split(factor=0.23)
        split.label(text="Thumbnail size:")
        split.prop(self, 'AD_thumbnail_size', text="", slider=True)

        row = layout.row()
        row.separator()
        row = layout.row()
        row.label(text="Batch Operation List:")
        row = layout.row()
        split = row.split(factor=0.2)
        split.label(text="Mode:")
        split.label(text="Filepath:")
        row = layout.row()
        row.template_list("AD_UL_Filelist", "Batch Render", self, "AD_batchrender_list",
                self, "AD_batchrender_list_index")
        row = layout.row(align=True)
        row.operator("ad.filelist_add", text="Add")
        row.operator("ad.filelist_remove", text="Remove")
        row.operator("ad.filelist_clear", text="Clear")
        row = layout.row(align=True)
        row.operator("ad.filelist_render", text="Render")
        row.operator("ad.filelist_package", text="Package textures")
        row = layout.row()
        row.operator("ad.filelist_relocate", text="Relocate")

class WM_OT_drop_blend_file(Operator):
    bl_idname = "wm.drop_blend_file"
    bl_label = "Handle dropped .blend file"
    bl_options = {'INTERNAL'}

    filepath: StringProperty()

    def invoke(self, context, _event):
        context.window_manager.popup_menu(
                self.draw_menu,
                title=bpy.path.basename(self.filepath),
                icon='QUESTION')
        return {'FINISHED'}

    def draw_menu(self, menu, _context):
        layout = menu.layout

        col = layout.column()
        col.operator_context = 'INVOKE_DEFAULT'
        props = col.operator("wm.open_mainfile", text="Open", icon='FILE_FOLDER')
        props.filepath = self.filepath
        props.display_file_selector = False

        layout.separator()
        col = layout.column()
        col.operator_context = 'INVOKE_DEFAULT'
        col.operator("wm.link",
                    text="Link...",
                    icon='LINK_BLEND').filepath = self.filepath
        col.operator("wm.append",
                    text="Append...",
                    icon='APPEND_BLEND').filepath = self.filepath


        if hasattr(bpy.types, "AD_OT_merge_mat_from_blend"):
            layout.separator()
            col = layout.column()
            col.operator_context = 'INVOKE_DEFAULT'
            col.label(text="Aqueduct", icon_value=custom_icons["aqueduct_logo"].icon_id)
            col.operator("ad.merge_obj_from_blend",
                    text="Append Objects",
                    icon='APPEND_BLEND'
                    ).filepath = self.filepath

            col.operator("ad.merge_mat_from_blend",
                    text="Append Material",
                    icon='NODE_MATERIAL',
                    ).filepath = self.filepath

            col.operator("ad.merge_col_from_blend",
                    text="Append Collection",
                    icon='GROUP',
                    ).filepath = self.filepath
            
class VIEW3D_MT_PIE_Aqueduct(Menu):
    bl_label = "Aqueduct"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        tools = pie.box()
        tools.label(text="Tools:")
        tools.operator("ad.material_quickapply", icon='MATERIAL')
        tools.operator("ad.object_quickplace", icon='OBJECT_ORIGIN')
        tools.operator("ad.object_quickrotate", icon='FILE_REFRESH')
        export = pie.box()
        export.label(text="Export:")
        export.operator("ad.save_material_filedialog", icon='EXPORT')
        export.operator("ad.save_object_filedialog", icon='EXPORT')
        export.operator("ad.save_collection_filedialog", icon='EXPORT')
        pie.operator("ad.open_settings", icon='PREFERENCES')

        # other = pie.column()
        # gap = other.column()
        # other_menu = other.box().column()
        # other_menu.operator("ad.open_settings")

unreg_classes = [
    AD_UL_ListItem,
    AD_UL_Filelist,
    VIEW3D_MT_PIE_Aqueduct,
    AD_Preferences,
        ]

reg_classes = [
        WM_OT_drop_blend_file,
        *unreg_classes
        ]

custom_icons = None

def register():
    # Custom icon loading
    global custom_icons
    custom_icons = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "resources")
    custom_icons.load("aqueduct_logo", os.path.join(icons_dir, "aqueduct_logo_32.png"), 'IMAGE')

    from bpy.utils import register_class
    for cls in reg_classes:
        register_class(cls)

def unregister():
    global custom_icons
    bpy.utils.previews.remove(custom_icons)

    from bpy. utils import unregister_class
    for cls in unreg_classes:
        unregister_class(cls)
