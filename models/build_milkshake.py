import math, random, os, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import trimesh
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt

ROOT=Path(r"C:\Users\Administrator\Desktop\Agencia\site_nogit")
OUT=ROOT/"models"
TEX=OUT/"milkshake_textures"
TEX.mkdir(exist_ok=True)
random.seed(27)
np.random.seed(27)

# High-resolution procedural chocolate/cream swirl texture, wrapped around a tapered cup.
W=2048; H=2048
# Vectorized organic cream ribbons with layered chocolate, subtle marbling and fine grain.
small=Image.fromarray(np.uint8(np.random.rand(128,128)*255)).resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
noise=np.asarray(small,dtype=np.float32)/255.0
yy,xx=np.mgrid[0:H,0:W]
v=yy/(H-1)
# Winding cream ribbons: the angular pattern drifts with height to mimic hand-swirled shake.
phase=(2*math.pi*(xx/W*2.55) + 1.35*np.sin(v*math.pi*2.0)
       + .62*np.sin(v*math.pi*5.4) + (noise-.5)*1.15)
cream=np.sin(phase) > .20
# A few broad uneven swaths cross the cup, matching the photographed layered mix.
for lo,hi in [(0.16,0.23),(0.46,0.53),(0.76,0.83)]:
    wobble=(noise-.5)*.075 + .025*np.sin(xx/W*math.pi*5)
    cream |= (v > lo+wobble) & (v < hi+wobble) & (noise>.23)
grain=np.random.normal(0,2.8,(H,W,1))
choc=np.array([119,68,43],dtype=np.float32)
pale=np.array([235,204,177],dtype=np.float32)
base=np.where(cream[:,:,None],pale,choc)
streak=(.93+.12*(noise[:,:,None]-.5)+.025*np.sin(xx[:,:,None]/W*math.pi*24+v[:,:,None]*31))
rgb=np.clip(base*streak+grain,0,255).astype(np.uint8)
# Thin irregular chocolate veins through the cream ribbons.
veins=(~cream)&(noise>.88)&(np.sin(xx/W*math.pi*19+v*13)>.1)
rgb[veins]=np.clip(rgb[veins]*.65+np.array([190,145,113])*.35,0,255).astype(np.uint8)
arr=np.dstack([rgb,np.full((H,W),255,dtype=np.uint8)])
smooth_tex=Image.fromarray(arr,"RGBA")
smooth_tex.save(TEX/"milkshake_marble.png")

# Transparent cup with subtle cool PET tint and fine highlights.
cup_tex=Image.new("RGBA",(512,512),(210,231,235,40))
cup_tex.save(TEX/"cup_tint.png")

# Label: vivid green/purple AÇAI DUTOP emblem inspired by the supplied sticker.
label=Image.new("RGBA",(1024,1024),(0,0,0,0))
ld=ImageDraw.Draw(label)
ld.ellipse((35,35,989,989),fill=(66,207,55,255),outline=(24,125,65,255),width=24)
ld.ellipse((90,100,934,920),fill=(115,23,164,255),outline=(178,62,205,255),width=16)
# leaf-like green arcs
ld.pieslice((40,0,980,530),185,355,fill=(66,218,42,255),outline=(22,130,75,255),width=14)
ld.pieslice((25,520,1000,1050),5,178,fill=(70,218,42,255),outline=(22,130,75,255),width=14)
try:
    font1=ImageFont.truetype("arialbd.ttf",158)
    font2=ImageFont.truetype("arialbd.ttf",104)
except:
    font1=ImageFont.load_default(); font2=font1
ld.text((512,420),"AÇAÍ",font=font1,fill=(255,79,188,255),anchor="mm",stroke_width=3,stroke_fill=(93,15,110,255))
ld.text((512,590),"DUTOP",font=font2,fill=(177,255,49,255),anchor="mm",stroke_width=3,stroke_fill=(37,88,22,255))
label.save(TEX/"acai_dutop_label.png")

# Straw stripes texture, white with diagonal red bands.
straw=Image.new("RGB",(512,512),(247,247,242))
sd=ImageDraw.Draw(straw)
for x in range(-600,1100,100):
    sd.polygon([(x,0),(x+36,0),(x+548,512),(x+512,512)],fill=(225,49,61))
straw.save(TEX/"straw_stripes.png")

def mat(color,rough=.45,metal=0,alpha=1,tex=None,double=False):
    kwargs=dict(baseColorFactor=color,roughnessFactor=rough,metallicFactor=metal,alphaMode=("BLEND" if alpha<1 else "OPAQUE"),doubleSided=double)
    if tex is not None: kwargs["baseColorTexture"]=tex
    return trimesh.visual.material.PBRMaterial(**kwargs)

cream_mat=mat([235,204,177,255],.34)
choc_mat=mat([119,68,43,255],.31)
marble_mat=mat([255,255,255,255],.42,tex=smooth_tex)
clear_mat=mat([222,239,244,54],.12,alpha=.20,double=True)
lid_mat=mat([237,247,249,105],.12,alpha=.36,double=True)
white_mat=mat([247,247,242,255],.32)
red_mat=mat([220,43,55,255],.36)
label_mat=mat([255,255,255,255],.45,tex=label,double=True)
straw_mat=mat([255,255,255,255],.3,tex=straw)

def lathe(profile, material, name, segments=128, vmap=None):
    # profile: (radius, y) rings; UV wraps horizontally and vertically.
    verts=[]; uvs=[]
    for j,(r,y) in enumerate(profile):
        for i in range(segments):
            a=2*math.pi*i/segments
            verts.append([r*math.cos(a),y,r*math.sin(a)])
            uvs.append([i/segments, j/max(1,len(profile)-1) if vmap is None else vmap(j,y)])
    faces=[]
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i; b=j*segments+(i+1)%segments
            c=(j+1)*segments+(i+1)%segments; d=(j+1)*segments+i
            faces.extend([[a,b,c],[a,c,d]])
    mesh=trimesh.Trimesh(vertices=np.array(verts),faces=np.array(faces),process=False)
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.array(uvs),material=material)
    mesh.metadata["name"]=name
    return mesh

def cylinder_y(radius,height,y,material,name,sections=96):
    profile=[(radius,y-height/2),(radius,y+height/2)]
    return lathe(profile,material,name,sections)

def sphere(pos,scale,material,name):
    m=trimesh.creation.icosphere(subdivisions=2,radius=1)
    m.apply_scale(scale); m.apply_translation(pos)
    m.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(m.vertices),2)),material=material)
    m.metadata["name"]=name
    return m

parts=[]
# Cup outer shell: 16 oz tapered PET cup, open top and thick molded base.
cup_profile=[(.031,.012),(.032,.025),(.034,.055),(.038,.20),(.042,.38),(.046,.57),(.048,.70),(.049,.735)]
parts.append(lathe(cup_profile,clear_mat,"Transparent tapered PET cup",160))
# Interior shake surface, same taper and height, with a subtle rounded top.
shake_profile=[(.030,.025),(.031,.055),(.035,.20),(.039,.38),(.043,.57),(.046,.70),(.0465,.715),(.044,.724),(.038,.729),(.020,.731),(.001,.731)]
parts.append(lathe(shake_profile,marble_mat,"Chocolate and cream marbled milkshake",160))
# Thick bottom plug and foot.
parts.append(lathe([(.030,.006),(.033,.012),(.032,.023),(.030,.028)],choc_mat,"Milkshake base",128))
parts.append(lathe([(.030,.002),(.034,.004),(.034,.012),(.031,.016)],lid_mat,"Molded cup foot",128))
# Clear lid flange with raised concentric lip and shallow dome.
parts.append(lathe([(.047,.735),(.052,.741),(.055,.750),(.055,.758),(.052,.764),(.049,.766),(.048,.760)],lid_mat,"Clear snap-on lid flange",160))
parts.append(lathe([(.050,.758),(.049,.770),(.046,.779),(.040,.784),(.030,.787),(.012,.788),(.001,.788)],lid_mat,"Clear domed lid",160))
# Fine embossed concentric rim lines.
for yy,rr in [(.747,.054),(.756,.055),(.765,.050)]:
    parts.append(lathe([(rr-.0008,yy-.001),(rr,yy),(rr-.0008,yy+.001)],clear_mat,"Lid embossed rim",160))
# Straw, tall, white with diagonal red stripes, visible through lid opening.
parts.append(lathe([(.0048,.775),(.0048,1.055),(.0042,1.058)],straw_mat,"Red striped paper straw",48))
parts.append(lathe([(.0038,.775),(.0038,1.055)],white_mat,"Straw inner bore",48))
# Front sticker, curved onto front of cup. A small curved patch with UV label.
# orient on -Z front; create shallow curved panel.
verts=[]; uv=[]; faces=[]
for iy in range(2):
    yy=.38+iy*.135
    for ix in range(65):
        a=-.48 + .96*ix/64
        r=.0495 + (yy-.38)*.025
        verts.append([r*math.sin(a),yy,-r*math.cos(a)])
        uv.append([ix/64,iy])
for ix in range(64):
    faces.extend([[ix,ix+1,65+ix+1],[ix,65+ix+1,65+ix]])
sticker=trimesh.Trimesh(vertices=np.array(verts),faces=np.array(faces),process=False)
sticker.visual=trimesh.visual.TextureVisuals(uv=np.array(uv),material=label_mat)
sticker.metadata["name"]="Açai Dutop front brand sticker"
parts.append(sticker)
# Condensation droplets on exposed cup surface; understated, varied size.
droplet_mat=mat([232,246,249,145],.08,alpha=.55)
for i in range(72):
    a=random.uniform(-math.pi,math.pi)
    y=random.uniform(.10,.68)
    r=.032 + (y/.735)*.017
    sz=random.uniform(.0007,.0022)
    parts.append(sphere([r*math.cos(a),y,r*math.sin(a)],[sz,sz*1.5,sz*.45],droplet_mat,"Condensation droplet"))

# Compress the vertical coordinates to realistic 15 cm cup / 21 cm total dimensions.
for m in parts:
    m.vertices[:,1] *= 0.20
    m._cache.clear()
scene=trimesh.Scene()
for i,m in enumerate(parts):
    scene.add_geometry(m,node_name=f"milkshake_part_{i:03d}",geom_name=m.metadata.get("name",f"part{i}"))
glb=scene.export(file_type="glb")
(OUT/"milkshake_acai_dutop.glb").write_bytes(glb)
print("GLB created",len(glb),"bytes",len(parts),"parts")

# Build matching USDZ using Pixar USD with Preview Surface materials and UV textures.
stage_path=OUT/"milkshake_acai_dutop.usdc"
stage=Usd.Stage.CreateNew(str(stage_path))
root=UsdGeom.Xform.Define(stage,"/Milkshake")
stage.SetDefaultPrim(root.GetPrim())
UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage,1.0)

def usd_material(name, color, rough=.4, opacity=1, texture=None):
    mtl=UsdShade.Material.Define(stage,f"/Milkshake/Looks/{name}")
    shader=UsdShade.Shader.Define(stage,f"/Milkshake/Looks/{name}/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor",Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness",Sdf.ValueTypeNames.Float).Set(rough)
    shader.CreateInput("opacity",Sdf.ValueTypeNames.Float).Set(opacity)
    if texture:
        uv=UsdShade.Shader.Define(stage,f"/Milkshake/Looks/{name}/UVTexture")
        uv.CreateIdAttr("UsdUVTexture")
        uv.CreateInput("file",Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("milkshake_textures/"+Path(texture).name))
        reader=UsdShade.Shader.Define(stage,f"/Milkshake/Looks/{name}/PrimvarReader")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname",Sdf.ValueTypeNames.Token).Set("st")
        reader.CreateOutput("result",Sdf.ValueTypeNames.Float2)
        uv.CreateInput("st",Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),"result")
        uv.CreateOutput("rgb",Sdf.ValueTypeNames.Float3)
        shader.CreateInput("diffuseColor",Sdf.ValueTypeNames.Color3f).ConnectToSource(uv.ConnectableAPI(), "rgb")
    shader.CreateOutput("surface",Sdf.ValueTypeNames.Token)
    mtl.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),"surface")
    return mtl

usd_mats={
 "marble":usd_material("MilkshakeMarble",(0.48,.25,.14),.34,1,TEX/"milkshake_marble.png"),
 "clear":usd_material("TransparentPET",(.82,.91,.94),.1,.19),
 "lid":usd_material("ClearLid",(.9,.96,.98),.12,.35),
 "choc":usd_material("Chocolate",(0.38,.18,.09),.3,1),
 "label":usd_material("AcaiDutopLabel",(.5,.1,.7),.4,1,TEX/"acai_dutop_label.png"),
 "straw":usd_material("StripedStraw",(.95,.95,.9),.3,1,TEX/"straw_stripes.png"),
 "drop":usd_material("Condensation",(.85,.94,.98),.08,.55)
}
def assign_usd_texture(prim, texture_path):
    pv=UsdGeom.PrimvarsAPI(prim).CreatePrimvar("st",Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying)
    return pv

for i,m in enumerate(parts):
    path=f"/Milkshake/Part_{i:03d}"
    mesh=UsdGeom.Mesh.Define(stage,path)
    pts=[Gf.Vec3f(float(v[0]),float(v[1]),float(v[2])) for v in m.vertices]
    mesh.CreatePointsAttr(pts)
    mesh.CreateFaceVertexCountsAttr([3]*len(m.faces))
    mesh.CreateFaceVertexIndicesAttr([int(v) for v in m.faces.flatten()])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    uv=getattr(getattr(m,"visual",None),"uv",None)
    if uv is not None and len(uv)==len(m.vertices):
        # Convert vertex UVs to face-varying UVs.
        stvals=[Gf.Vec2f(float(uv[idx][0]),float(uv[idx][1])) for idx in m.faces.flatten()]
        primvar=UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st",Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying)
        primvar.Set(stvals)
        matname="marble" if i==1 else ("clear" if i==0 else ("choc" if i==2 else ("lid" if 3<=i<=8 else ("straw" if i in (9,10) else ("label" if i==11 else "drop")))))
    else:
        matname="drop"
    UsdShade.MaterialBindingAPI(mesh).Bind(usd_mats[matname])
    mesh.GetPrim().SetCustomDataByKey("displayName",m.metadata.get("name",f"Part {i}"))
stage.GetRootLayer().Save()
# USDZ: uncompressed ZIP with root USDC first, then relative textures.
usdz=OUT/"milkshake_acai_dutop.usdz"
with zipfile.ZipFile(usdz,"w",compression=zipfile.ZIP_STORED) as z:
    z.write(stage_path,"milkshake_acai_dutop.usdc")
    for f in TEX.glob("*.png"):
        z.write(f,"milkshake_textures/"+f.name)
stage_path.unlink()
print("USDZ created",usdz.stat().st_size,"bytes")
