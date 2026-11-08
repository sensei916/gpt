# Eye of Horus v3 - hardcore part-by-part build (Beretta 1301 Tactical, Hoshino livery)
# mm authored -> m. Bore axis X (muzzle +X), Z up, left side +Y, right side -Y
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

M = 0.001
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

# ======================= materials =======================
def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    return nt, nt.nodes['Principled BSDF'], nt.nodes['Material Output']

def bump_tex(nt, b, kind, scale, strength, dist=0.0003, direction='X', coords='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if kind == 'noise':
        t = nt.nodes.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = scale; t.inputs['Detail'].default_value = 6
        out = t.outputs['Fac']
    elif kind == 'voronoi':
        t = nt.nodes.new('ShaderNodeTexVoronoi'); t.inputs['Scale'].default_value = scale
        out = t.outputs['Distance']
    elif kind == 'wave':
        t = nt.nodes.new('ShaderNodeTexWave'); t.wave_type = 'BANDS'; t.bands_direction = direction
        t.wave_profile = 'SIN'; t.inputs['Scale'].default_value = scale; t.inputs['Distortion'].default_value = 0
        out = t.outputs['Fac']
    nt.links.new(tc.outputs[coords], t.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength; bp.inputs['Distance'].default_value = dist
    nt.links.new(out, bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return t

def rough_var(nt, b, lo, hi, scale=80):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 8
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = lo; mr.inputs['To Max'].default_value = hi
    nt.links.new(n.outputs['Fac'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])

def pbr(name, base, rough=0.5, metal=0.0, coat=0.0, rv=0.08, bump=None, emit=None):
    m = bpy.data.materials.new(name); nt, b, o = _nodes(m)
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.2
    if rv: rough_var(nt, b, max(0.03, rough - rv), min(1, rough + rv))
    if bump: bump_tex(nt, b, *bump)
    if emit:
        b.inputs['Emission Color'].default_value = (*emit[0], 1); b.inputs['Emission Strength'].default_value = emit[1]
    return m

def cerakote(name, base, stipple=False):
    # painted white over black metal, with edge wear via pointiness
    m = bpy.data.materials.new(name); nt, b, o = _nodes(m)
    b.inputs['Base Color'].default_value = (*base, 1); b.inputs['Roughness'].default_value = 0.48
    b.inputs['Coat Weight'].default_value = 0.08
    rough_var(nt, b, 0.38, 0.6, 60)
    if stipple: bump_tex(nt, b, 'voronoi', 2600, 0.45, 0.0004)
    else: bump_tex(nt, b, 'noise', 3000, 0.12, 0.0002)
    w = nt.nodes.new('ShaderNodeBsdfPrincipled')
    w.inputs['Base Color'].default_value = (0.09, 0.09, 0.095, 1); w.inputs['Metallic'].default_value = 1; w.inputs['Roughness'].default_value = 0.3
    g = nt.nodes.new('ShaderNodeNewGeometry')
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.54; cr.color_ramp.elements[1].position = 0.6
    nt.links.new(g.outputs['Pointiness'], cr.inputs['Fac'])
    tc = nt.nodes.new('ShaderNodeTexCoord'); n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 220; n.inputs['Detail'].default_value = 10
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    cr2 = nt.nodes.new('ShaderNodeValToRGB'); cr2.color_ramp.elements[0].position = 0.5; cr2.color_ramp.elements[1].position = 0.62
    nt.links.new(n.outputs['Fac'], cr2.inputs['Fac'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(cr.outputs['Color'], mul.inputs[0]); nt.links.new(cr2.outputs['Color'], mul.inputs[1])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mul.outputs[0], mix.inputs['Fac'])
    nt.links.new(b.outputs['BSDF'], mix.inputs[1]); nt.links.new(w.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], o.inputs['Surface'])
    return m

MAT = {
 'white':   cerakote('WhiteCerakote', (0.82, 0.82, 0.80)),
 'stipple': cerakote('WhiteStipple', (0.80, 0.80, 0.78), True),
 'park':    pbr('BlackParkerized', (0.030, 0.030, 0.033), 0.42, 0.9, 0, 0.1, ('noise', 1800, 0.15)),
 'anod':    pbr('BlackAnodized', (0.022, 0.022, 0.025), 0.32, 0.85, 0, 0.06),
 'poly':    pbr('BlackPolymer', (0.025, 0.025, 0.027), 0.58, 0, 0, 0.06, ('noise', 2500, 0.25)),
 'pink':    pbr('PinkAnodized', (0.95, 0.36, 0.55), 0.28, 0.75, 0, 0.05),
 'pinkknurl': pbr('PinkKnurl', (0.95, 0.36, 0.55), 0.3, 0.75, 0, 0.05, ('wave', 260, 0.9, 0.0005, 'X')),
 'knurl':   pbr('BlackKnurl', (0.03, 0.03, 0.033), 0.4, 0.9, 0, 0.05, ('wave', 260, 0.9, 0.0005, 'X')),
 'chrome':  pbr('BoltChrome', (0.72, 0.72, 0.74), 0.14, 1.0, 0, 0.05, ('noise', 900, 0.05)),
 'nitride': pbr('NitrideSteel', (0.12, 0.12, 0.13), 0.3, 1.0, 0, 0.06),
 'hull':    pbr('ShellHull', (0.50, 0.035, 0.045), 0.32, 0, 0.35, 0.04, ('wave', 1400, 0.25, 0.0002, 'Z')),
 'brass':   pbr('Brass', (0.88, 0.62, 0.30), 0.2, 1.0, 0, 0.06),
 'primer':  pbr('Primer', (0.78, 0.76, 0.72), 0.25, 1.0),
 'rubber':  pbr('Rubber', (0.018, 0.018, 0.018), 0.82, 0, 0, 0.05, ('wave', 420, 0.7, 0.0006, 'Z')),
 'fiber':   pbr('FiberRed', (1.0, 0.04, 0.06), 0.2, 0, 0.6, 0, None, ((1, 0.05, 0.05), 3.0)),
 'engr':    pbr('EngraveDark', (0.02, 0.02, 0.02), 0.7, 0, 0, 0),
 'stamp':   pbr('StampSilver', (0.55, 0.55, 0.56), 0.35, 1.0, 0, 0),
 'cavity':  pbr('Cavity', (0.01, 0.01, 0.01), 0.6, 0, 0, 0),
}

# ======================= helpers =======================
ROOT = bpy.data.objects.new('GunRoot', None); col.objects.link(ROOT)
PART = {}
def part(name):
    e = bpy.data.objects.new('Part_' + name, None); col.objects.link(e); e.parent = ROOT
    e.empty_display_size = 0.02; PART[name] = e; return e
CUR = [None]

def finish(o, m, bevel=0.6, seg=3, parent=None, angle=35, smooth=True):
    o.data.materials.append(MAT[m])
    if bevel:
        bm = o.modifiers.new('Bevel', 'BEVEL'); bm.width = bevel * M; bm.segments = seg
        bm.limit_method = 'ANGLE'; bm.angle_limit = math.radians(angle)
    wn = o.modifiers.new('WN', 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    o.parent = parent or CUR[0]
    return o

def fillet(pts, r, n=6):
    P = [Vector(p) for p in pts]; N = len(P); out = []
    for i in range(N):
        ri = r[i] if isinstance(r, (list, tuple)) else r
        A, C, B = P[i - 1], P[i], P[(i + 1) % N]
        da, db = A - C, B - C
        t = min(ri, 0.45 * da.length, 0.45 * db.length)
        if t <= 1e-6: out.append(C.copy()); continue
        S = C + da.normalized() * t; E = C + db.normalized() * t
        for k in range(n + 1):
            u = k / n; out.append((1 - u) ** 2 * S + 2 * (1 - u) * u * C + u * u * E)
    return [(v.x, v.y) for v in out]

def extrude(name, pts, axis, a0, a1, m, bevel=0.8, seg=3, parent=None, r=0, angle=35, cutter=False):
    if r: pts = fillet(pts, r)
    me = bpy.data.meshes.new(name); bmh = bmesh.new()
    def V(u, v, a):
        if axis == 'Y': return bmh.verts.new((u * M, a * M, v * M))
        if axis == 'X': return bmh.verts.new((a * M, u * M, v * M))
        return bmh.verts.new((u * M, v * M, a * M))
    f = [V(u, v, a1) for u, v in pts]; b = [V(u, v, a0) for u, v in pts]
    bmh.faces.new(f); bmh.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bmh.faces.new([f[i], b[i], b[j], f[j]])
    bmesh.ops.recalc_face_normals(bmh, faces=bmh.faces)
    bmh.to_mesh(me); bmh.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    if cutter:
        o.hide_render = True; o.display_type = 'WIRE'; o.parent = parent or CUR[0]; return o
    return finish(o, m, bevel, seg, parent, angle)

def side(name, pts, y0, y1, m, **k):  # side profile (x,z) extruded along Y
    return extrude(name, pts, 'Y', y0, y1, m, **k)

def box(name, x0, x1, y0, y1, z0, z1, m='anod', bevel=0.5, **k):
    return side(name, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1, m, bevel=bevel, **k)

def cyl(name, axis, c, r, length, m, verts=48, bevel=0.4, r2=None, parent=None, cutter=False):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r * M, radius2=(r2 if r2 is not None else r) * M,
                                    depth=length * M, location=[v * M for v in c])
    o = bpy.context.active_object; o.name = name
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    if axis == 'Y': o.rotation_euler = (math.radians(-90), 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if cutter:
        o.hide_render = True; o.display_type = 'WIRE'; o.parent = parent or CUR[0]; return o
    return finish(o, m, bevel, 2, parent)

def xcyl(name, x0, x1, r, z=0, y=0, m='park', **k):
    return cyl(name, 'X', ((x0 + x1) / 2, y, z), r, x1 - x0, m, **k)

def cut(target, cutter, arr=None):
    if arr:
        a = cutter.modifiers.new('Arr', 'ARRAY'); a.use_relative_offset = False; a.use_constant_offset = True
        a.constant_offset_displace = Vector(arr[1]) * M; a.count = arr[0]
    md = target.modifiers.new('Bool_' + cutter.name, 'BOOLEAN'); md.object = cutter; md.solver = 'EXACT'
    try:
        target.modifiers.move(len(target.modifiers) - 1, 0)
    except Exception as ex:
        print('MOVEFAIL', ex)
    return md

def text(name, body, loc, rot, size, m='engr', depth=0.15, align='CENTER', font=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size * M; cu.extrude = depth * M
    cu.align_x = align; cu.align_y = 'CENTER'
    if font: cu.font = font
    o = bpy.data.objects.new(name, cu); col.objects.link(o)
    o.location = [v * M for v in loc]; o.rotation_euler = [math.radians(a) for a in rot]
    o.data.materials.append(MAT[m]); o.parent = CUR[0]; return o

def screw(name, loc, axis, r=2.6, m='anod'):
    s = cyl(name, axis, loc, r, 1.6, m, 24, 0.5)
    d = {'Y': (0, 0.9 if loc[1] > 0 else -0.9, 0), 'X': (0.9, 0, 0), 'Z': (0, 0, 0.9)}[axis]
    cyl(name + '_skt', axis, tuple(loc[i] + d[i] for i in range(3)), r * 0.45, 0.4, 'cavity', 6, 0)
    return s

FONT = None
for fp in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
    if os.path.exists(fp): FONT = bpy.data.fonts.load(fp); break

# ======================= 01 RECEIVER =======================
CUR[0] = part('receiver')
rec = side('Receiver', [(-38, -38), (186, -38), (192, -30), (192, 14), (184, 24), (150, 28), (-20, 28), (-38, 18)], -17, 17, 'white', bevel=4, seg=5, r=6)
cut(rec, box('cut_loadport', 36, 150, -11, 11, -45, -26, cutter=True))
cut(rec, box('cut_ejport', 72, 140, -30, -6, -5, 17, cutter=True))
cut(rec, side('cut_flute', [(0, -22), (176, -22), (176, -19.6), (0, -19.6)], -30, 30, None, cutter=True))
cut(rec, side('cut_flute2', [(10, 6), (60, 6), (60, 8.4), (10, 8.4)], 10, 30, None, cutter=True))
box('Lifter', 38, 148, -10.5, 10.5, -34, -30, 'nitride', 0.6)
box('PortCavity', 72, 140, -12, -9, -5, 17, 'cavity', 0)
for i, x in enumerate([28, 112]):
    cyl(f'TrigPin{i}', 'Y', (x, 0, -30), 2.6, 35.2, 'nitride', 24, 0.3)
cyl('BoltReleaseBtn', 'Y', (58, -17.6, -20), 5.2, 3.2, 'pink', 32, 0.6)
side('CarrierLatch', [(130, -34), (150, -34), (150, -28), (130, -28)], -18.2, -16.8, 'pink', bevel=0.6, r=2)
if FONT:
    text('TxtBeretta', 'BERETTA', (95, 17.3, -6), (90, 0, 180), 9, 'engr', 0.12, font=FONT)
    text('TxtModel', '1301 TACTICAL', (95, 17.3, -30), (90, 0, 180), 4.2, 'engr', 0.12, font=FONT)
    text('TxtHorus', 'EYE OF HORUS', (-6, -17.3, 6), (90, 0, 0), 4.6, 'pink', 0.12, font=FONT)
    text('TxtSerial', 'AB-0102  KIVOTOS', (30, -17.3, -30), (90, 0, 0), 3.0, 'engr', 0.1, font=FONT)

# ======================= 02 BOLT CARRIER GROUP =======================
CUR[0] = part('bolt')
BOLT = bpy.data.objects.new('BoltRig', None); col.objects.link(BOLT); BOLT.parent = CUR[0]
CUR[0] = BOLT
side('BoltCarrier', [(70, -2), (136, -2), (140, 2), (140, 15), (70, 15)], -15.5, 4, 'chrome', bevel=0.8, r=2)
side('CarrierCut', [(84, 9), (124, 9), (124, 15.5), (84, 15.5)], -15.8, -12, 'nitride', bevel=0.3)
xcyl('BoltHead', 140, 158, 7.5, z=6.5, y=-4, m='chrome', verts=40)
for i in range(4):
    a = i * math.pi / 2 + math.pi / 4
    box(f'BoltLug{i}', 152, 158, -4 + 7 * math.cos(a) - 1.8, -4 + 7 * math.cos(a) + 1.8, 6.5 + 7 * math.sin(a) - 1.8, 6.5 + 7 * math.sin(a) + 1.8, 'chrome', 0.3)
box('Extractor', 140, 160, -12.6, -10.8, 4, 9, 'nitride', 0.3)
cyl('ChargingRod', 'Y', (118, -25, 8), 3.6, 22, 'chrome', 24, 0.3)
cyl('ChargingKnob', 'Y', (118, -40, 8), 8.6, 12, 'pinkknurl', 48, 0.8)
cyl('ChargingKnobCap', 'Y', (118, -46.6, 8), 7.2, 1.4, 'pink', 48, 0.5)

# ======================= 03 TRIGGER GROUP =======================
CUR[0] = part('trigger')
side('TriggerHousing', [(12, -38), (128, -38), (128, -50), (118, -58), (22, -58), (12, -48)], -14, 14, 'poly', bevel=1.5, r=3)
g = side('TriggerGuard', [(30, -56), (118, -56), (114, -78), (100, -88), (44, -88), (30, -76)], -5, 5, 'poly', bevel=1.6, r=[2, 2, 10, 10, 10, 6])
cut(g, side('cut_guard', [(38, -58), (110, -58), (106, -76), (96, -82), (50, -82), (38, -72)], -8, 8, None, r=[1, 1, 8, 8, 8, 4], cutter=True))
side('Trigger', [(78, -57), (84, -57), (82, -64), (77, -72), (70, -77), (67, -75), (73, -68), (77, -62)], -3, 3, 'pink', bevel=0.8, r=1.5)
cyl('SafetyBolt', 'Y', (104, 0, -50), 3.6, 34, 'pink', 32, 0.4)
cyl('SafetyRing', 'Y', (104, 14.6, -50), 4.6, 1.2, 'anod', 32, 0.3)

# ======================= 04 PISTOL GRIP =======================
CUR[0] = part('grip')
side('PistolGrip', [(-18, -40), (26, -46), (18, -70), (12, -76), (10, -84), (5, -90), (3, -98), (-1, -104), (-4, -112),
                    (-8, -132), (-10, -150), (-48, -156), (-58, -146), (-40, -80), (-30, -56)], -15, 15, 'stipple', bevel=6, seg=5, r=4)
side('GripCap', [(-10, -150), (-48, -156), (-50, -162), (-12, -158)], -13, 13, 'pink', bevel=1.5, r=2)
screw('GripScrew', (-30, -15.2, -120), 'Y', 3.2)

# ======================= 05 STOCK =======================
CUR[0] = part('stock')
stk = side('Stock', [(-38, 26), (-110, 30), (-200, 32), (-330, 40), (-346, 40), (-346, -92), (-330, -92), (-250, -76), (-160, -58), (-110, -50), (-38, -38)],
           -18, 18, 'white', bevel=12, seg=6, r=[4, 20, 20, 6, 3, 3, 6, 20, 20, 12, 4])
cut(stk, side('cut_thumb', [(-128, -12), (-250, -24), (-300, -30), (-300, -62), (-250, -60), (-150, -44)], -40, 40, None, r=10, cutter=True))
side('CheekRiser', [(-130, 30), (-310, 38), (-312, 48), (-140, 42)], -15, 15, 'white', bevel=5, seg=4, r=5)
side('RecoilPad', [(-346, 42), (-372, 44), (-376, 30), (-376, -86), (-372, -96), (-346, -94)], -19, 19, 'rubber', bevel=5, seg=4, r=4)
box('PadInsert', -347, -345, -12, 12, -70, 20, 'poly', 0.4)
for i, z in enumerate([20, -70]):
    screw(f'PadScrew{i}', (-376.8, 0, z), 'X', 2.6)
cyl('QDCup', 'Y', (-300, 18.2, -80), 7, 3, 'anod', 32, 0.4)
cyl('QDCupHole', 'Y', (-300, 19.3, -80), 4.2, 1.2, 'cavity', 32, 0)
cyl('AbydosRing', 'Y', (-215, 18.4, -2), 15, 1.0, 'pink', 64, 0.3)
cyl('AbydosDisc', 'Y', (-215, 18.9, -2), 12.5, 1.0, 'white', 64, 0.2)
if FONT:
    text('TxtAbydos', 'ABYDOS', (-215, 19.5, -2), (90, 0, 180), 5.4, 'pink', 0.15, font=FONT)
side('StockStripe', [(-302, -86), (-296, -86), (-296, 38), (-302, 38)], -18.7, 18.7, 'pink', bevel=0.4)

# ======================= 06 BARREL =======================
CUR[0] = part('barrel')
xcyl('BarrelShoulder', 186, 222, 16.5, verts=64)
xcyl('Barrel', 222, 664, 12.8, verts=64, r2=11.2)
box('VentRib', 222, 652, -3.8, 3.8, 18, 21, 'park', 0.4)
for i in range(16):
    x = 230 + i * 26
    box(f'RibPost{i}', x, x + 5, -2.2, 2.2, 10, 18.2, 'park', 0.3)
box('SightBase', 640, 654, -3.2, 3.2, 20.5, 25, 'anod', 0.5)
xcyl('FiberRod', 641, 653, 1.2, z=24.2, m='fiber', verts=16)
if FONT:
    text('TxtBarrel1', '12 GA  3"  CYL', (300, -13.4, 1), (90, 0, 0), 3.2, 'stamp', 0.08, font=FONT)
    text('TxtBarrel2', 'GARDONE V.T.  ITALY', (300, 13.4, 1), (90, 0, 180), 3.2, 'stamp', 0.08, font=FONT)
ch = xcyl('Choke', 664, 722, 14.4, verts=64)
xcyl('ChokeKnurl', 704, 720, 14.9, m='knurl', verts=64)
cut(ch, xcyl('cut_bore', 690, 730, 9.4, cutter=True))
for j, x in enumerate([674, 684, 694]):
    for k in range(4):
        a = k * math.pi / 4
        c = cyl(f'cut_port{j}_{k}', 'Z', (x, 0, 0), 2.3, 40, None, 16, cutter=True)
        c.rotation_euler = (a, 0, 0)
        cut(ch, c)

# ======================= 07 MAGAZINE TUBE =======================
CUR[0] = part('mag')
xcyl('MagTube', 186, 560, 13, z=-28, verts=56)
xcyl('MagJoint', 556, 566, 14, z=-28, m='anod', verts=56)
xcyl('MagExtension', 566, 640, 13.4, z=-28, verts=56)
xcyl('MagCap', 640, 660, 15.6, z=-28, m='pinkknurl', verts=64)
cyl('MagCapDome', 'X', (662, 0, -28), 14.4, 4, 'pink', 64, 1.2)
cyl('SlingLoop', 'Z', (666, 0, -28), 4.5, 18, 'anod', 24, 0.5)

# ======================= 08 BARREL CLAMP =======================
CUR[0] = part('clamp')
extrude('BarrelClamp', [(-17, -46), (17, -46), (17, 18), (-17, 18)], 'X', 598, 620, 'anod', bevel=2, seg=3, r=8)
for i, z in enumerate([-8, -38]):
    screw(f'ClampBolt{i}', (609, -17.8, z), 'Y', 3.4, 'nitride')
bpy.ops.mesh.primitive_torus_add(major_radius=7 * M, minor_radius=1.8 * M, location=(609 * M, 0, -54 * M))
t = bpy.context.active_object; t.name = 'ClampSling'; t.rotation_euler = (0, math.radians(90), 0)
finish(t, 'anod', 0)

# ======================= 09 FOREND =======================
CUR[0] = part('forend')
fe = side('Forend', [(198, -50), (430, -50), (442, -42), (444, -10), (436, -2), (198, -2)], -24, 24, 'white', bevel=10, seg=6, r=[4, 8, 6, 6, 6, 4])
cut(fe, box('cut_mlok', 236, 268, -40, 40, -33, -24, cutter=True), arr=(4, (44, 0, 0)))
cut(fe, box('cut_ribs', 210, 222, -40, 40, -44, -42.6, cutter=True), arr=(1, (0, 0, 0)))
xcyl('ForendBore', 198, 444, 13.3, z=-28, m='cavity', verts=32)
side('ForendRing', [(437, -45), (446, -45), (446, -6), (437, -6)], -21, 21, 'pink', bevel=1.2, r=3)

# ======================= 10 TOP RAIL =======================
CUR[0] = part('rail')
rail = extrude('TopRail', [(-8, 0), (8, 0), (8, 2), (10.6, 4.6), (10.6, 6.6), (8, 9.4), (-8, 9.4), (-10.6, 6.6), (-10.6, 4.6), (-8, 2)], 'X', -14, 188, 'anod', bevel=0.4)
for o_ in [rail]:
    o_.location.z = 28 * M
c = box('cut_railslot', -6, -0.8, -15, 15, 33.5, 40, cutter=True)
cut(rail, c, arr=(19, (10, 0, 0)))
rail.location.z = 28 * M; c.location.z = 0
for i, x in enumerate([10, 90, 170]):
    screw(f'RailScrew{i}', (x, 0, 37.6), 'Z', 2.4, 'nitride')

# ======================= 11 SIDE SADDLE =======================
CUR[0] = part('saddle')
side('SaddlePlate', [(40, -32), (168, -32), (168, 22), (40, 22)], 17, 20.5, 'anod', bevel=0.8, r=6)
for i, (x, z) in enumerate([(48, 14), (160, 14), (48, -24), (160, -24)]):
    screw(f'SaddleScrew{i}', (x, 21, z), 'Y', 2.4, 'nitride')
sb = side('SaddleBody', [(56, -30), (164, -30), (164, 10), (56, 10)], 20.5, 34, 'poly', bevel=2, r=4)
cut(sb, cyl('cut_cups', 'Z', (66, 33, -10), 10.7, 60, None, 32, cutter=True), arr=(6, (17.6, 0, 0)))
for i in range(6):
    x = 66 + i * 17.6
    cyl(f'ShellHull{i}', 'Z', (x, 33, 12), 10.3, 56, 'hull', 40, 0.5)
    cyl(f'ShellCrimp{i}', 'Z', (x, 33, 41.5), 10.3, 3, 'hull', 40, 0.6, r2=7.5)
    cyl(f'ShellBrass{i}', 'Z', (x, 33, -20), 10.6, 9, 'brass', 40, 0.4)
    cyl(f'ShellRim{i}', 'Z', (x, 33, -25), 11.2, 1.4, 'brass', 40, 0.3)
    cyl(f'ShellPrimer{i}', 'Z', (x, 33, -25.9), 2.7, 0.6, 'primer', 24, 0.1)

# ======================= ejected shell =======================
CUR[0] = BOLT.parent
SHELL = bpy.data.objects.new('EjectShell', None); col.objects.link(SHELL); SHELL.parent = PART['receiver']
CUR[0] = SHELL
cyl('EjHull', 'X', (6, 0, 0), 10.3, 56, 'hull', 40, 0.5)
cyl('EjCrimp', 'X', (35.5, 0, 0), 10.3, 3, 'hull', 40, 0.6, r2=7.5)
cyl('EjBrass', 'X', (-26, 0, 0), 10.6, 9, 'brass', 40, 0.4)
cyl('EjRim', 'X', (-31, 0, 0), 11.2, 1.4, 'brass', 40, 0.3)
cyl('EjPrimer', 'X', (-31.9, 0, 0), 2.7, 0.6, 'primer', 24, 0.1)

# ======================= stage =======================
w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']; out = nt.nodes['World Output']
hdrs = []
for r_, d_, fs in os.walk(os.environ.get('ASSETS', 'assets')):
    hdrs += [os.path.join(r_, f_) for f_ in fs if f_.endswith(('.hdr', '.exr'))]
if hdrs:
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdrs[0])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.4
else:
    bg.inputs['Color'].default_value = (0.05, 0.05, 0.055, 1)
lp = nt.nodes.new('ShaderNodeLightPath'); mix = nt.nodes.new('ShaderNodeMixShader')
bk = nt.nodes.new('ShaderNodeBackground'); bk.inputs['Color'].default_value = (0.010, 0.010, 0.012, 1)
nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
nt.links.new(bg.outputs['Background'], mix.inputs[1]); nt.links.new(bk.outputs['Background'], mix.inputs[2])
nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])

bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, -0.30))
fl = bpy.context.active_object; fl.name = 'Floor'
fl.data.materials.append(pbr('Floor', (0.025, 0.025, 0.027), 0.5, 0, 0, 0.3, ('noise', 400, 0.3)))

def area(name, loc, size, energy, color=(1, 1, 1), sy=None, tgt=(0.15, 0, 0)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size; l.color = color
    if sy: l.shape = 'RECTANGLE'; l.size_y = sy
    o = bpy.data.objects.new(name, l); col.objects.link(o); o.location = loc
    d = Vector(tgt) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o
area('Key', (0.4, -1.4, 1.2), 1.4, 320, (1, 0.97, 0.93), 0.6)
area('Fill', (-0.6, 1.5, 0.6), 1.6, 90, (0.9, 0.93, 1.0))
area('RimPink', (-1.0, 0.3, 0.45), 0.6, 170, (1.0, 0.55, 0.75), 1.6)
area('RimCool', (1.4, 0.8, 0.4), 0.5, 120, (0.7, 0.8, 1.0), 1.4)
area('Top', (0.15, 0, 1.8), 2.2, 110)

def camera(name, loc, target, lens=50, fstop=None):
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_width = 36; c.clip_start = 0.01
    o = bpy.data.objects.new(name, c); col.objects.link(o); o.location = loc
    t = bpy.data.objects.new(name + '_tgt', None); col.objects.link(t); t.location = target
    tr = o.constraints.new('TRACK_TO'); tr.target = t; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    if fstop: c.dof.use_dof = True; c.dof.aperture_fstop = fstop; c.dof.focus_object = t
    return o
camExp = camera('CamExplode', (0.95, -1.75, 0.95), (0.12, 0, -0.02), 40, 8)
camWide = camera('CamWide', (0.17, -1.95, 0.30), (0.17, 0, -0.03), 50, 6)
camLeft = camera('CamLeft', (0.17, 1.95, 0.25), (0.17, 0, -0.03), 50, 6)
camClose = camera('CamClose', (0.24, -0.42, 0.10), (0.10, -0.02, -0.01), 60, 2.8)
camHero = camera('CamHero', (1.15, -0.95, 0.26), (0.12, 0, -0.03), 70, 4)
camDet = camera('CamDetail', (0.80, -0.22, 0.06), (0.69, 0, 0), 85, 2.0)

# ======================= animation =======================
sc.frame_start, sc.frame_end = 1, 240; sc.render.fps = 24
def key(o, path, f, val):
    setattr(o, path, val); o.keyframe_insert(path, frame=f)
EXPLODE = {  # part: offset (m)
 'stock': (-0.20, 0, 0.02), 'grip': (-0.04, 0, -0.20), 'trigger': (0.02, 0, -0.13), 'bolt': (0.02, -0.16, 0.05),
 'rail': (0, 0, 0.12), 'barrel': (0.22, 0, 0.08), 'mag': (0.24, 0, -0.10), 'forend': (0.12, 0, -0.18),
 'clamp': (0.34, 0, 0.16), 'saddle': (0.02, 0.17, 0.02),
}
order = ['stock', 'grip', 'trigger', 'bolt', 'rail', 'barrel', 'mag', 'forend', 'clamp', 'saddle']
for i, pn in enumerate(order):
    e = PART[pn]; off = Vector(EXPLODE[pn])
    s = 18 + i * 6
    key(e, 'location', 1, off); key(e, 'location', s, off * 1.04); key(e, 'location', s + 20, (0, 0, 0))
key(PART['receiver'], 'location', 1, (0, 0, 0))
# whole gun: slow drift during assembly, then turntable
key(ROOT, 'rotation_euler', 1, (0, 0, math.radians(-12)))
key(ROOT, 'rotation_euler', 90, (0, 0, math.radians(0)))
key(ROOT, 'rotation_euler', 91, (0, 0, math.radians(-25)))
key(ROOT, 'rotation_euler', 160, (0, 0, math.radians(-25 + 360)))
key(ROOT, 'rotation_euler', 161, (0, 0, 0))
key(ROOT, 'rotation_euler', 240, (0, 0, math.radians(6)))
# bolt cycle
key(BOLT, 'location', 1, (0, 0, 0)); key(BOLT, 'location', 170, (0, 0, 0))
key(BOLT, 'location', 180, (-0.066, 0, 0)); key(BOLT, 'location', 190, (-0.066, 0, 0)); key(BOLT, 'location', 193, (0, 0, 0))
# ejected shell
for ch_ in SHELL.children:
    key(ch_, 'hide_render', 1, True); key(ch_, 'hide_render', 175, True); key(ch_, 'hide_render', 176, False); key(ch_, 'hide_render', 205, False); key(ch_, 'hide_render', 206, True)
key(SHELL, 'location', 176, (0.104, -0.008, 0.006)); key(SHELL, 'rotation_euler', 176, (0, 0, 0))
key(SHELL, 'location', 186, (0.090, -0.150, 0.080)); key(SHELL, 'rotation_euler', 186, (math.radians(80), math.radians(30), math.radians(260)))
key(SHELL, 'location', 204, (0.050, -0.360, -0.120)); key(SHELL, 'rotation_euler', 204, (math.radians(190), math.radians(90), math.radians(640)))
# cams
key(camExp, 'location', 1, (1.05, -1.90, 1.05)); key(camExp, 'location', 90, (0.75, -1.55, 0.55))
key(camClose, 'location', 161, (0.26, -0.43, 0.10)); key(camClose, 'location', 205, (0.20, -0.39, 0.09))
key(camHero, 'location', 206, (1.15, -0.95, 0.26)); key(camHero, 'location', 240, (0.98, -0.80, 0.22))
for f, c in [(1, camExp), (91, camWide), (161, camClose), (206, camHero)]:
    mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
sc.camera = camExp

r = sc.render; r.resolution_x, r.resolution_y = 1280, 720
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = 40; sc.cycles.use_denoising = True; sc.cycles.adaptive_threshold = 0.03; sc.cycles.max_bounces = 6
r.image_settings.file_format = 'PNG'
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get('OUT', '.') + '/eye_of_horus.blend')
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type in ('MESH','CURVE','FONT') and not o.hide_render and o.name != 'Floor':
        d = o.evaluated_get(dg).dimensions
        if max(d) > 0.2: print('BIGOBJ', o.name, tuple(round(v,3) for v in d), tuple(round(v,3) for v in o.matrix_world.translation))
print('BUILD_OK', len(bpy.data.objects))
