import bpy, os, sys
a = sys.argv[sys.argv.index('--')+1:]
mode = a[0]
sc = bpy.context.scene
out = os.environ.get('OUT', '.')
sc.cycles.device = 'CPU'
if mode == 'stills':
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.cycles.samples = 128
    sys.path.insert(0, os.getcwd()); from shots import SHOTS as shots
    only = a[1]
    for n, c, f in shots:
        if n != only: continue
        sc.timeline_markers.clear(); sc.frame_set(f); sc.camera = bpy.data.objects[c]
        sc.render.filepath = f'{out}/still_{n}.png'
        bpy.ops.render.render(write_still=True)
else:
    s, e = int(a[1]), int(a[2])
    sc.frame_start, sc.frame_end = s, e
    sc.cycles.samples = 40
    sc.render.filepath = f'{out}/f_'
    bpy.ops.render.render(animation=True)
