# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_drawing_split

import bpy
from bpy.types import Object, Operator, Panel
import bmesh

bl_info = {
    "name": "Drawings Split",
    "description": "Split drawings by border",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 4),
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
        borders = context.selected_objects[:]
        borders_aabb = [(border, cls._aabb_2d(border)) for border in borders]
        # check only meshes, not borders, not instances
        checking_objects = (obj for obj in context.blend_data.objects
                            if obj not in borders
                            and obj.type == 'MESH'
                            and obj.users == 1)
        # check objects
        cls._deselect_all(context=context)
        future_selection = []   # for future additional selection
        for obj in checking_objects:
            cls._deselect_all_vertices(obj=obj)
            # for each object to check
            for border, border_aabb in borders_aabb:
                # check for each border
                border_points_closed_sequence = cls._points_sorted(obj=border)
                # first - check by bounding boxes
                if cls._collision_aabb(cls._aabb_2d(obj), border_aabb):
                    # if aabb have collision
                    polygon = [(v_co_world.x, v_co_world.y) for v_co_world in
                               (border.matrix_world * vertex.co for vertex in border_points_closed_sequence)]
                    # check each point of checking object
                    for point in cls._points_xy(obj=obj):
                        # check if object point is inside border
                        rez = cls._point_inside_polygon(
                            polygon=polygon,
                            point=point[1]
                        )
                        # select if point inside border
                        point[0].select = (point[0].select or rez)
                # selected vertices
                selected = len([v for v in obj.data.vertices if v.select])
                all_vertices = len(obj.data.vertices)
                # if selected and selected != all_vertices:
                if selected:
                    # if object has points inside border (now selected)
                    if selected != all_vertices:
                        # and there ara not all points of the object - split selected points to another object
                        context.scene.objects.active = obj
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.mesh.separate(type='SELECTED')
                        bpy.ops.object.mode_set(mode='OBJECT')
                    else:
                        # has selected objects and all of them are inside border (whole object inside border)
                        #   mark for future selection
                        future_selection.append(obj)
        # add to future selection all currently selected objects - stayed selected objects inside borders
        for obj in context.selected_objects:
            future_selection.append(obj)
        # join border objects back
        cls._deselect_all(context=context)
        for obj in borders:
            obj.select = True
        context.scene.objects.active = context.selected_objects[0]
        bpy.ops.object.join()
        # select objects that has all points inside border
        for obj in future_selection:
            obj.select = True

    @staticmethod
    def _deselect_all_vertices(obj: Object):
        # deselect all vertices for object (in OBJECT mode)
        for p in obj.data.polygons:
            p.select = False
        for e in obj.data.edges:
            e.select = False
        for v in obj.data.vertices:
            v.select = False

    @staticmethod
    def _collision_aabb(bbox_1, bbox_2):
        # check collision of two axis aligned bounding boxes
        if bbox_1['min_x'] < bbox_2['max_x'] \
                and bbox_1['max_x'] > bbox_2['min_x'] \
                and bbox_1['min_y'] < bbox_2['max_y'] \
                and bbox_1['max_y'] > bbox_2['min_y']:
            return True
        else:
            return False

    @classmethod
    def _aabb_2d(cls, obj: Object):
        # get aligned bounding box for mesh in X-Y projection
        x, y = zip(*(p[1] for p in cls._points_xy(obj=obj)))
        return {
            "min_x": min(x),
            "min_y": min(y),
            "max_x": max(x),
            "max_y": max(y)
        }

    @staticmethod
    def _points_xy(obj: Object):
        # get points in X-Y projection in world coordinate system
        return ((v_co_world[0], (v_co_world[1].x, v_co_world[1].y)) for v_co_world in
                ((vertex, obj.matrix_world * vertex.co) for vertex in obj.data.vertices))

    @staticmethod
    def _points_sorted(obj):
        # get points sorted by order for a border object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # create a list with sorted indices of mesh vertices
        vertices_indices_sorted = []
        vertex = bm.verts[0]
        l = len(bm.verts)
        i = 0
        while vertex is not None:
            vertices_indices_sorted.append(vertex.index)
            edge = next((_edge for _edge in vertex.link_edges
                         if _edge.other_vert(vertex).index not in vertices_indices_sorted), None)
            vertex = edge.other_vert(vertex) if edge else None
            # alarm break
            i += 1
            if i > l:
                print('_points_sorted() err exit')
                break
        # add first to last to close loop
        vertices_indices_sorted.append(vertices_indices_sorted[0])
        # return full sequence
        return [obj.data.vertices[i] for i in vertices_indices_sorted]

    @staticmethod
    def _point_inside_polygon(polygon, point):
        # check if point is inside polygon in X-Y projection
        # polygon - closed sorted sequence of point coordinates, point - coordinates
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
