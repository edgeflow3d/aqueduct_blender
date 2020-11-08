import json
import os
from shutil import copyfile

import bpy

from bpy.types import Operator, PropertyGroup 
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty

from .ad_utils import *

class AD_TYPE_Resource(PropertyGroup):
    selected: BoolProperty(name="Selected", default=False)

class AD_OT_center_objects(Operator):
    bl_idname = "ad.center_objects"
    bl_label = "Center objects"
    bl_options = {'INTERNAL'}

    pivot : StringProperty(default='-Z')

    def execute(self, context):

        # Case: Nothing selected
        if len(context.selected_objects) == 0:
            return {'CANCELLED'}

        self.objects = context.selected_objects
        ws_extents = get_ws_min_max(self.objects)

        center = get_center(ws_extents, self.pivot)

        distance = Vector((0,0,0)) - center

        for obj in self.objects:
            obj.location += distance

        return {'FINISHED'}

class AD_OT_open_settings(Operator):
    """ Opens the Aqueduct addon settings """
    bl_idname = "ad.open_settings"
    bl_label = "Open Aqueduct settings"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = 'Aqueduct'

        return {'FINISHED'}

class AD_OT_export_resource(Operator):
    bl_idname = "ad.export_resource"
    bl_label = "Export Resource"
    bl_options = {'INTERNAL'}

    filepath : StringProperty(
            default="",
            subtype='FILE_PATH'
            )

    mode : EnumProperty(name="Mode",
            items=[
                ('OBJECT', "Object", 'OBJECT_DATA', 0),
                ('MATERIAL', "Material", 'MATERIAL', 1),
                ('COLLECTION', "Collection", 'GROUP', 2),
                ])

    blocknames : StringProperty(default="")
    pivot : StringProperty(default='-Z')
    package_images: BoolProperty(default=False)

    def execute(self, context):
        # restore namelist from string
        blocknamelist = json.loads(self.blocknames)

        # get the resources based on their name
        self.datablocks = []

        if self.mode == 'OBJECT':
            for name in blocknamelist:
                if name in bpy.data.objects.keys():
                    self.datablocks.append(bpy.data.objects[name])

        if self.mode == 'COLLECTION':
            for name in blocknamelist:
                if name in bpy.data.collections.keys():
                    self.datablocks.append(bpy.data.collections[name])

        if self.mode == 'MATERIAL':
            for name in blocknamelist:
                if name in bpy.data.materials.keys():
                    self.datablocks.append(bpy.data.materials[name])

        # write them to the tempfile
        lib_path = os.path.join(os.path.abspath(bpy.app.tempdir), "ad_res_tmp.blend")
        if bpy.app.version[1] < 90:
            bpy.data.libraries.write(lib_path, set(self.datablocks), relative_remap=True)
        else:
            bpy.data.libraries.write(lib_path, set(self.datablocks), path_remap='RELATIVE_ALL') 

        # write cleanup script
        scriptpath = self.write_lib_cleanup_script(self.filepath)

        # cleanup and save the file
        background_worker(scriptpath, lib_path)

        return {'FINISHED'}

    def write_lib_cleanup_script(self, save_path):
        scriptpath = os.path.join(bpy.app.tempdir, "ad_res_script.py")
        script = open(scriptpath, 'w', encoding='utf-8')

        script.write("import bpy\n")
        script.write("context = bpy.context\n")
        script.write("scene = context.scene\n")

        # rename the scene from Empty to Scene
        script.write("scene.name = 'Scene'\n")

        if self.mode == 'OBJECT':
            # link the resources to the master collection
            script.write("for obj in bpy.data.objects:\n")
            script.write("    scene.collection.objects.link(obj)\n")

            # center the objects around origin
            script.write("bpy.ops.object.select_all(action='SELECT')\n")
            script.write("bpy.ops.ad.center_objects(pivot='{}')\n".format(self.pivot))

        if self.mode == 'COLLECTION':
            # link all collections to the scene master collection
            script.write("for col in bpy.data.collections:\n")
            script.write("    scene.collection.children.link(col)\n")

            # center the objects around origin
            script.write("bpy.ops.object.select_all(action='SELECT')\n")
            script.write("bpy.ops.ad.center_objects(pivot='{}')\n".format(self.pivot))

        if self.mode == 'MATERIAL':
            # create geometry to hold the materials
            # TODO: Bevel geometry
            script.write("for i, mat in enumerate(bpy.data.materials):\n")
            script.write("    bpy.ops.mesh.primitive_cube_add(location=(4*i, 0, 0))\n")
            script.write("    bpy.ops.object.material_slot_add()\n")
            script.write("    bpy.context.active_object.material_slots[0].material = mat\n")

        # save the file
        # disable blend1 files just in case of overwriting of existing blendfiles
        script.write("bpy.context.preferences.filepaths.save_version = 0\n")
        script.write("bpy.ops.wm.save_as_mainfile(filepath='{}')\n".format(save_path))

        if self.package_images:
            # relink
            script.write("bpy.ops.ad.package_images()\n")
            # save after relinking
            script.write("bpy.ops.wm.save_as_mainfile(filepath='{}')\n".format(save_path))

        script.close()

        return scriptpath

class AD_OT_relocate_file(Operator):
    """ moves the blendfile and its resources to a new location """
    bl_idname = "ad.relocate_file"
    bl_label = "Relocate Blendfile and resources"
    bl_options = {'INTERNAL'}

    source : StringProperty(name="Source", default='', subtype='FILE_PATH')
    destination : StringProperty(default='', subtype='FILE_PATH')

    def execute(self, context):
        log("executing {}".format(self.bl_idname))
        log("Source: {}".format(self.source))
        log("Destination: {}".format(self.destination))

        # write the script
        scriptpath = self.write_relocate_script()

        # call background worker
        background_worker(scriptpath, filepath=self.source)


        return {'FINISHED'}

    def write_relocate_script(self):
        scriptpath = os.path.join(bpy.app.tempdir, "ad_relocate_script.py")
        script = open(scriptpath, 'w', encoding='utf-8')

        script.write("import bpy\n")

        # save file to the new location
        script.write("bpy.context.preferences.filepaths.save_version = 0\n")
        script.write("bpy.ops.wm.save_as_mainfile(filepath='{}')\n".format(self.destination))

        # package its assets next to it
        script.write("bpy.ops.ad.package_images()\n")

        # save again
        script.write("bpy.ops.wm.save_mainfile()\n")

        script.close()

        return scriptpath

class AD_OT_package_images(Operator):
    """ gathers images, packages and relinks paths """
    bl_idname = "ad.package_images"
    bl_label = "Package textures"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        log("executing {}".format(self.bl_idname))

        images = bpy.data.images

        # GUARD CLAUSES
        # Case: No images in file
        if len(images) == 0:
            self.report({'INFO'}, "No texture images in this file")
            return {'CANCELLED'}

        # Case: Images in file but all unused
        images_unused = True
        for image in images:
            if image.users > 0:
                images_unused = False
        if images_unused:
            self.report({'INFO'}, "None of the images in this file are being used")
            return {'CANCELLED'}


        # make a textures folder next to blendfile if it doesn't exist
        filepath = bpy.data.filepath
        dirpath = os.path.join(os.path.dirname(filepath), "textures")

        # Case: No write permission
        if not os.path.exists(dirpath):
            try:
                os.mkdir(dirpath)
            except PermissionError:
                self.report({'ERROR'}, "Can't write files, no write permission")
                return {'CANCELLED'}

        relink_count = 0
        for image in images:
            if image.users > 0:

                # copy the image to a texture folder next to the blendfile
                file_src = bpy.path.abspath(image.filepath)
                file_dest = os.path.join(dirpath, bpy.path.basename(image.filepath))
                if os.path.exists(file_src):
                    if not os.path.exists(file_dest):
                        copyfile(file_src, file_dest)

                    # relink the image filepaths to the new location
                    image.filepath = bpy.path.relpath(file_dest)
                    relink_count += 1
                # if the image is packed into the blend
                elif image.packed_file != None:
                    # unpack() will put the image into a textures folder next to the blend
                    # and relink the image node
                    image.unpack()

        log("Relinked {} images!".format(relink_count))
        return {'FINISHED'}

class AD_OT_package_images_batch(Operator):
    bl_idname = "ad.package_images_batch"
    bl_label = "Package images batch"
    bl_options = {'INTERNAL'}

    filepath : StringProperty(
            default="",
            subtype='FILE_PATH'
            )

    def execute(self, context):

        #GUARD CLAUSES

        # Case: Filepath is invalid
        if os.path.exists(self.filepath) == False:
            self.report({'ERROR'}, "Filepath of file to render is invalid")
            return {'CANCELLED'}

        context.window.cursor_set('WAIT')
        # Write Script file
        scriptpath = self.write_package_script()
        # Call Background worker to render
        background_worker(scriptpath, self.filepath)

        context.window.cursor_set('DEFAULT')
        return {'FINISHED'}

    def write_package_script(self):
        scriptpath = os.path.join(bpy.app.tempdir, "ad_package_script.py")
        script = open(scriptpath, 'w', encoding='utf-8')

        script.write("import bpy\n")

        # Package images and relink image nodes
        script.write("bpy.ops.ad.package_images()\n")

        # Save the file and disable backup versions (no .blend1)
        script.write("bpy.context.preferences.filepaths.save_version = 0\n")
        script.write("bpy.ops.wm.save_mainfile()\n")

        script.close()

        return scriptpath

class AD_OT_render_thumbnail(Operator):
    bl_idname = "ad.render_thumbnail"
    bl_label = "Render thumbnail"
    bl_options = {'INTERNAL'}

    filepath : StringProperty(
            default="",
            subtype='FILE_PATH'
            )

    mode : EnumProperty(name="Mode",
            items=[
                ('OBJECT', "Object", 'OBJECT_DATA', 0),
                ('MATERIAL', "Material", 'MATERIAL', 1)
                ])

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences

        #GUARD CLAUSES

        # Case: Filepath is invalid
        if os.path.exists(self.filepath) == False:
            self.report({'ERROR'}, "Filepath of file to render is invalid")
            return {'CANCELLED'}

        # Case: Studio files do not exist
        if self.mode == 'OBJECT' and os.path.exists(prefs.AD_object_studio_path) == False:
            self.report({'ERROR'}, "Path to Studio blendfile is invalid")
            return {'CANCELLED'}

        if self.mode == 'MATERIAL' and os.path.exists(prefs.AD_material_studio_path) == False:
            self.report({'ERROR'}, "Path to Studio blendfile is invalid")
            return {'CANCELLED'}
        context.window.cursor_set('WAIT')
        if self.mode == 'OBJECT':
            # Write Script file
            scriptpath = self.write_objrender_script(self.filepath)
            # Call Background worker to render
            background_worker(scriptpath, prefs.AD_object_studio_path)

        else:
            scriptpath = self.write_matrender_script(self.filepath)
            background_worker(scriptpath, prefs.AD_material_studio_path)


        context.window.cursor_set('DEFAULT')
        return {'FINISHED'}

    def write_objrender_script(self, blend_filepath):
        prefs = bpy.context.preferences.addons[__package__].preferences
        studio_path = prefs.AD_object_studio_path
        thumbnail_size = prefs.AD_thumbnail_size
        scriptpath = os.path.join(bpy.app.tempdir, "ad_objrender_script.py")
        thumbnail_path = os.path.splitext(blend_filepath)[0]
        script = open(scriptpath, 'w', encoding='utf-8')

        script.write("import bpy\n")

        script.write("context = bpy.context\n")
        script.write("scene = context.scene\n")
        script.write("prefs = context.preferences.addons['{}'].preferences\n".format(__package__))

        # merge all objects from the blendfile
        script.write("with bpy.data.libraries.load('{}') as (data_from, data_to):\n".format(
            blend_filepath))
        script.write("    data_to.objects = data_from.objects\n")

        # link all objects to the scene and select them
        script.write("for obj in data_to.objects:\n")
        script.write("    scene.collection.objects.link(obj)\n")
        script.write("    obj.select_set(True)\n")

        # frame all objects with camera
        script.write("scene.camera.data.lens += 5\n")
        script.write("bpy.ops.view3d.camera_to_view_selected()\n")
        script.write("scene.camera.data.lens -= 5\n")

        # render frame
        script.write("render = scene.render\n")
        script.write("render.resolution_x = {}\n".format(thumbnail_size))
        script.write("render.resolution_y = {}\n".format(thumbnail_size))
        script.write("render.use_file_extension = True\n")
        script.write("render.filepath='{}'\n".format(thumbnail_path))

        script.write("bpy.ops.render.render(write_still=True)\n")

        script.close()

        return scriptpath

    def write_matrender_script(self, blend_filepath):
        prefs = bpy.context.preferences.addons[__package__].preferences
        studio_path = prefs.AD_material_studio_path
        thumbnail_size = prefs.AD_thumbnail_size
        scriptpath = os.path.join(bpy.app.tempdir, "ad_matrender_script.py")
        thumbnail_path = os.path.splitext(blend_filepath)[0]

        script = open(scriptpath, 'w', encoding='utf-8')

        script.write("import bpy\n")

        script.write("context = bpy.context\n")
        script.write("scene = context.scene\n")
        script.write("prefs = context.preferences.addons['{}'].preferences\n".format(__package__))

        # merge all materials from the blendfile
        script.write("with bpy.data.libraries.load('{}') as (data_from, data_to):\n".format(
            blend_filepath))
        script.write("    data_to.materials = data_from.materials\n")

        script.write("materials = data_to.materials\n")

        # get material geo
        script.write("matgeo = [obj for obj in scene.objects if 'MATGEO' in obj.name]\n")

        script.write("for geo in matgeo:\n")
        # create matslots on geo if it doesn't have em
        script.write("    if len(geo.material_slots) == 0:\n")
        script.write("        context.view_layer.objects.active = geo\n")
        script.write("        bpy.ops.object.material_slot_add()\n")
        # assign first material to geo
        script.write("    geo.material_slots[0].material = materials[0]\n")

        # setup render settings
        script.write("render = scene.render\n")
        script.write("render.resolution_x = {}\n".format(thumbnail_size))
        script.write("render.resolution_y = {}\n".format(thumbnail_size))
        script.write("render.use_file_extension = True\n")
        script.write("render.filepath = '{}'\n".format(thumbnail_path))

        # render frame
        script.write("bpy.ops.render.render(write_still=True)\n")

        script.close()

        return scriptpath


classes = (
    AD_TYPE_Resource,
    AD_OT_export_resource,
    AD_OT_open_settings,
    AD_OT_render_thumbnail,
    AD_OT_relocate_file,
    AD_OT_center_objects,
    AD_OT_package_images,
    AD_OT_package_images_batch,
        )

register, unregister = bpy.utils.register_classes_factory(classes)
