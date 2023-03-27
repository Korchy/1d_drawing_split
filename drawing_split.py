# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_drawing_split

import bpy
from bpy.types import Operator, Panel
import bmesh

bl_info = {
    "name": "Drawings Split",
    "description": "Split drawings by border",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > DrewingsSplit",
    "doc_url": "https://github.com/Korchy/1d_drawing_split",
    "tracker_url": "https://github.com/Korchy/1d_drawing_split",
    "category": "All"
}

## MAIN CLASS

class DrawingSplit:

    @classmethod
    def split(cls, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        # split border object to separate borders (by loose parts) and save to list
        cls._deselect_all(context=context)
        context.object.select = True
        bpy.ops.mesh.separate(type='LOOSE')
        borders_list = context.selected_objects[:]
        # split all objects by loose parts
        cls._select_all(context=context)
        # don't split borders
        for obj in borders_list:
            obj.select = False
        # don't split instances (when try - loose all instances except the first)
        for obj in context.blend_data.objects:
            if obj.data.users > 1:
                obj.select = False
        bpy.ops.mesh.separate(type='LOOSE')
        # for each border object - get objects inside it
        for border in borders_list:
            cls._deselect_all(context=context)
            # get border points
            border_points = cls._points_sorted(obj=border)
            border_points_global = [border.matrix_world * p.co for p in border_points]
            # border points coordinates in X-Y projection
            border_points_global_xy = [(p.x, p.y) for p in border_points_global]
            # get check objects - if object is inside border
            check_obj = (obj for obj in context.blend_data.objects
                         if obj.type == 'MESH' and obj not in borders_list)
            for obj in check_obj:
                inside = True
                for point in obj.data.vertices:
                    # objects points coordinates in X-Y projection
                    point_global = obj.matrix_world * point.co
                    point_global_xy = [point_global.x, point_global.y]
                    # check if object point is inside border
                    rez = cls._point_inside_polygon(
                        polygon=border_points_global_xy,
                        point=point_global_xy
                    )
                    if rez == 0:
                        inside = False
                        break
                # select object if all its points is inside border
                if inside:
                    obj.select = True
                else:
                    obj.select = False
            # jon selected objects
            if context.selected_objects:
                context.scene.objects.active = context.selected_objects[0]
                bpy.ops.object.join()
        # join border objects back
        cls._deselect_all(context=context)
        for obj in borders_list:
            obj.select = True
        context.scene.objects.active = context.selected_objects[0]
        bpy.ops.object.join()

    @staticmethod
    def _points_sorted(obj):
        # get points sorted by order for a border object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        # create a list with sorted indices of mesh vertices
        vertices_indices_sorted = []
        vertex = bm.verts[0]
        l = len(bm.verts)
        i = 0
        while vertex is not None:
            vertices_indices_sorted.append(vertex.index)
            edge = next((_edge for _edge in vertex.link_edges if _edge.verts[1] != vertex), None)
            vertex = edge.verts[1] if edge.verts[1].index not in vertices_indices_sorted else None
            # alarm break
            i += 1
            if i > l:
                break
        # add first to last to close loop
        vertices_indices_sorted.append(vertices_indices_sorted[0])
        # return full sequence
        return [obj.data.vertices[i] for i in vertices_indices_sorted]

    @staticmethod
    def _point_inside_polygon(polygon, point):
        # check if point is inside polygon in X-Y projection
        length = len(polygon) - 1
        dy2 = point[1] - polygon[0][1]
        intersections = 0
        ii = 0
        jj = 1
        while ii < length:
            dy = dy2
            dy2 = point[1] - polygon[jj][1]
            # consider only lines which are not completely above/bellow/right from the point
            if dy * dy2 <= 0.0 and (point[0] >= polygon[ii][0] or point[0] >= polygon[jj][0]):
                # non-horizontal line
                if dy < 0 or dy2 < 0:
                    f = dy * (polygon[jj][0] - polygon[ii][0]) / (dy - dy2) + polygon[ii][0]
                    if point[0] > f:
                        # if line is left from the point - the ray moving towards left, will intersect it
                        intersections += 1
                    elif point[0] == f:
                        # point on line
                        return 2
                # point on upper peak (dy2=dx2=0) or horizontal line (dy=dy2=0 and dx*dx2<=0)
                elif dy2 == 0 and (point[0] == polygon[jj][0] or (
                        dy == 0 and (point[0] - polygon[ii][0]) * (point[0] - polygon[jj][0]) <= 0)):
                    return 2
            ii = jj
            jj += 1
        # print 'intersections =', intersections
        return intersections & 1

    @staticmethod
    def _deselect_all(context):
        if context.active_object.mode == 'OBJECT':
            bpy.ops.object.select_all(action='DESELECT')
        elif context.active_object.mode == 'EDIT':
            bpy.ops.mesh.select_all(action='DESELECT')

    @staticmethod
    def _select_all(context):
        if context.active_object.mode == 'OBJECT':
            bpy.ops.object.select_all(action='SELECT')
        elif context.active_object.mode == 'EDIT':
            bpy.ops.mesh.select_all(action='SELECT')


## OPERATORS

class DrawingsSplit_OT_split(Operator):
    bl_idname = 'drawinds_split.split'
    bl_label = 'Split drawings'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        DrawingSplit.split(context=context)
        return {'FINISHED'}


## PANELS

class DrawingsSplit_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Drawings Split"
    bl_category = '1D'

    def draw(self, context):
        layout = self.layout
        layout.operator('drawinds_split.split', text='Split', icon='SPLITSCREEN')

## REGISTER

def register():
    bpy.utils.register_class(DrawingsSplit_OT_split)
    bpy.utils.register_class(DrawingsSplit_PT_panel)


def unregister():
    bpy.utils.unregister_class(DrawingsSplit_PT_panel)
    bpy.utils.unregister_class(DrawingsSplit_OT_split)


if __name__ == "__main__":
    register()
