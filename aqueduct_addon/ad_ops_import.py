import bpy

from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, CollectionProperty

from .ad_utils import *

from .ad_ops_utility import AD_TYPE_Resource

class AD_OT_append_obj(Operator):
    """ Append objects from dropped file """

    bl_idname = "ad.merge_obj_from_blend"
    bl_label = "Append Object"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath: StringProperty(name="Filepath")
    link: BoolProperty(name="Link Resource", default=False)
    resource_list: CollectionProperty(name="Object List", type=AD_TYPE_Resource)

    def invoke(self, context, event):
        # look into the file and gather list of objects
        self.resource_list.clear()
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for obj in data_from.objects:
                entry = self.resource_list.add()
                entry.name = obj

        # GUARD CLAUSES

        # Case: No objects in the file
        if len(self.resource_list) == 0:
            self.report({'ERROR'}, "The dropped file does not contain any objects")
            return {'CANCELLED'}

        # Case: Multiple objects in the file
        if len(self.resource_list) > 1:
            return context.window_manager.invoke_props_dialog(self, width=500)

        # Case: Single object in the file
        self.resource_list[0].selected = True
        return self.execute(context)


    def execute(self, context):

        # load chosen objects from the file
        self.selected_resources = []
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for i, entry in enumerate(self.resource_list):
                if entry.selected:
                    self.selected_resources.append(data_from.objects[i])

            data_to.objects = self.selected_resources

        if len(self.selected_resources) == 0:
            return {'CANCELLED'}

        for obj in context.selected_objects:
            obj.select_set(False)

        # link the loaded objects to the active collection
        # and select them
        active_collection = context.view_layer.active_layer_collection.collection
        for res in self.selected_resources:
            active_collection.objects.link(res)
            res.select_set(True)

            # move to the 3D cursor
            res.location = context.scene.cursor.location + res.location

        return {'FINISHED'}


    def draw(self, context):
        """ Draws the resource selection GUI """
        layout = self.layout
        col = layout.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)

class AD_OT_append_mat(Operator):
    """ Append materials from dropped file """

    bl_idname = "ad.merge_mat_from_blend"
    bl_label = "Append Material"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath: StringProperty(name="Filepath")
    link: BoolProperty(name="Link Resource", default=False)
    resource_list: CollectionProperty(name="Material List", type=AD_TYPE_Resource)

    def invoke(self, context, event):
        # look into the file but don't load any resources
        self.resource_list.clear()
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for mat in data_from.materials:
                entry = self.resource_list.add()
                entry.name = mat

        # GUARD CLAUSES

        # Case: No materials in the file
        if len(self.resource_list) == 0:
            self.report({'ERROR'}, "The dropped file does not contain any materials")
            return {'CANCELLED'}

        # Case: Multiple materials in the file
        if len(self.resource_list) > 1:
            return context.window_manager.invoke_props_dialog(self, width=500)

        # Case: Single material in the file
        # Select the first and only material automatically
        self.resource_list[0].selected = True
        return self.execute(context)

    def draw(self, context):
        """ Draws the resource selection GUI """
        layout = self.layout
        col = layout.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)
        

    def execute(self, context):

        # load chosen materials from the file
        self.selected_resources = []
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for i, entry in enumerate(self.resource_list):
                if entry.selected:
                    self.selected_resources.append(data_from.materials[i])

            data_to.materials = self.selected_resources

        # Case: No material chosen
        if len(self.selected_resources) == 0:
            return {'CANCELLED'}

        # Case: Multiple materials
        if len(self.selected_resources) > 1:
            self.report({'INFO'}, 
                    "Successfully imported {} materials".format(len(self.selected_resources)))
            return {'FINISHED'}

        # Guard: Exit Edit mode if in Edit mode
        if context.active_object != None:
            if context.active_object.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')

        # Case: Single material
        self.material = self.selected_resources[0]
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def modal(self, context, event):

        # set cursor
        context.window.cursor_set('PAINT_BRUSH')

        # set header text
        options = "LMB: Apply Material | Shift+LMB: Apply to all Slots | Esc/RMB: Cancel"
        context.area.header_text_set("Applying Material: {} | {}".format(
            self.selected_resources[0].name,
            options))

        # allow navigation to happen
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NOTHING'}:
            return {'PASS_THROUGH'}

        # raycast on left click
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            eval_obj, loc, norm, face_id = raycast_object(context, event)
            # log("RAYCAST\nOBJ:{}\nLOC:{}\nN:{}\nFACE:{}\n".format(eval_obj, loc, norm, face_id))

            # if raycast was successful
            if eval_obj:
                target = eval_obj.original

                # deselect all / select target
                for obj in context.selected_objects:
                    obj.select_set(False)

                target.select_set(True)
                context.view_layer.objects.active = target

                # add matslot if there is none
                if len(target.material_slots) == 0:
                    bpy.ops.object.material_slot_add()

                # Case: Multiple material slots on the object
                if len(target.material_slots) > 1:
                    # Case: apply to all slots
                    if event.shift:
                        for matslot in target.material_slots:
                            matslot.material = self.selected_resources[0]

                    # Case: apply to slot to which the clicked face belongs
                    else:
                        matslot_index = get_matslot_from_faceid(eval_obj, face_id)
                        target.material_slots[matslot_index].material = self.selected_resources[0]

                # Case: One material slot on the object
                if len(target.material_slots) == 1:
                    target.material_slots[0].material = self.selected_resources[0]


            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            # remove the loaded material from the file
            # if it was not assigned / has 0 users
            if self.material.users == 0:
                bpy.data.materials.remove(self.material)

            # reset header area text
            context.area.header_text_set(None)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

class AD_OT_append_col(Operator):
    """ Append collections from dropped file """

    bl_idname = "ad.merge_col_from_blend"
    bl_label = "Append Collection"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath: StringProperty(name="Filepath")
    link: BoolProperty(name="Link Resource", default=False)
    resource_list: CollectionProperty(name="Object List", type=AD_TYPE_Resource)

    def invoke(self, context, event):
        # look into the file and gather list of objects
        self.resource_list.clear()
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for col in data_from.collections:
                entry = self.resource_list.add()
                entry.name = col

        # GUARD CLAUSES

        # Case: No collections in the file
        # TODO: Exclude the Scene Collection from the list
        if len(self.resource_list) == 0:
            self.report({'ERROR'}, "The dropped file does not contain any collections")
            return {'CANCELLED'}

        # Case: Multiple collections in the file
        if len(self.resource_list) > 1:
            return context.window_manager.invoke_props_dialog(self, width=500)

        # Case: Single collection in the file
        self.resource_list[0].selected = True
        return self.execute(context)


    def draw(self, context):
        """ Draws the resource selection GUI """
        layout = self.layout
        col = layout.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)

    def execute(self, context):

        # load chosen collections from the file
        self.selected_resources = []
        with bpy.data.libraries.load(self.filepath, self.link, False) as (data_from, data_to):
            for i, entry in enumerate(self.resource_list):
                if entry.selected:
                    self.selected_resources.append(data_from.collections[i])

            data_to.collections = self.selected_resources

        # Case: No collections chosen
        if len(self.selected_resources) == 0:
            return {'CANCELLED'}

        # Case: Multiple Collections
        # TODO: Fix Bug; CLASH on collection with same name already in file
        # TODO: ??? Bug doesn't always happen figure out in what case it errors out
        log("Collections selected for merge: {}".format(self.selected_resources))

        # deselect all
        for obj in context.scene.objects:
            obj.select_set(False)

        # duplicates = []
        for res in self.selected_resources:
            parent_col = context.view_layer.active_layer_collection.collection
            # for child in parent_col.children:
            #     if res.name == child.name:
            #         duplicates.append(res.name)
            #         continue

            parent_col.children.link(res)
            # select objects inside the collections
            for obj in res.objects:
                obj.select_set(True)

                # Move to the 3D Cursor
                obj.location = context.scene.cursor.location + obj.location



        # if len(duplicates) != 0:
        #     self.report({'ERROR'}, "The following collections are already in this collection\n. {}".format(duplicates)) 

        return {'FINISHED'}

classes = (
        AD_OT_append_obj,
        AD_OT_append_col,
        AD_OT_append_mat
        )

register, unregister = bpy.utils.register_classes_factory(classes)
