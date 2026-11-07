// The 3D watch: a Galaxy Watch4 Classic 46 mm, one unit is a centimetre. One renderer per browser tab, kept
// alive for the whole render; scenes ask it for a picture and copy the result onto their own canvas.

import * as THREE from 'three';
import {staticFile} from 'remotion';
import {loadFont as loadRoboto} from '@remotion/google-fonts/Roboto';
import {loadFace, SCALE} from './face.js';
import type {Cam} from './timeline';

const W = 1920, H = 1080, FOV = 28;
export const pxPerCm = (dist: number) => H / (2 * dist * Math.tan((FOV / 2) * (Math.PI / 180)));
export const RING_CM = (216 / 225) * 1.78; // the face's ring, on the 1.78 cm screen

function strapGeometry() {
  const half = [[0, 0.16], [1.5, 0.16], [2.72, 0.2], [3.18, -0.22], [3.42, -1.05], [3.32, -2.2], [2.5, -3.4], [1.1, -4.12], [0, -4.25]];
  const loop = [...half, ...half.slice(1, -1).reverse().map(([y, z]) => [-y, z])];
  const curve = new THREE.CatmullRomCurve3(loop.map(([y, z]) => new THREE.Vector3(0, y, z)), true, 'centripetal');
  const along = 900, across = 28, w = 1.0, t = 0.13, r = 0.1;
  const section: number[][] = [];
  for (let i = 0; i < across; i++) { // a rounded rectangle: along the arm, then out from it
    const a = (i / across) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
    section.push([Math.sign(c) * (w - r) + c * r, Math.sign(s) * (t - r * 0.7) + s * r * 0.7, s]);
  }
  const pos: number[] = [], index: number[] = [];
  for (let i = 0; i < along; i++) {
    const u = i / along, p = curve.getPointAt(u), tan = curve.getTangentAt(u);
    const ny = -tan.z, nz = tan.y; // pointing away from the wrist
    for (const [x, out, top] of section) {
      const ribs = top > 0.5 ? 0.007 * Math.sin(u * 780) : 0; // the strap's fine ribs, on its outside only
      pos.push(x, p.y + ny * (out + ribs), p.z + nz * (out + ribs));
    }
  }
  for (let i = 0; i < along; i++) {
    for (let j = 0; j < across; j++) {
      const a = i * across + j, b = i * across + ((j + 1) % across);
      const c = ((i + 1) % along) * across + j, d = ((i + 1) % along) * across + ((j + 1) % across);
      index.push(a, c, b, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(index);
  g.computeVertexNormals();
  return g;
}

function lathe(points: number[][], material: THREE.Material) {
  const g = new THREE.LatheGeometry(points.map(([r, z]) => new THREE.Vector2(r, z)), 256);
  g.rotateX(Math.PI / 2);
  const m = new THREE.Mesh(g, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function lugGeometry() {
  const s = new THREE.Shape();
  s.moveTo(1.7, 0.1);
  s.lineTo(2.55, 0.1);
  s.quadraticCurveTo(2.85, 0.1, 3.0, 0.02);
  s.lineTo(3.06, 0.22);
  s.quadraticCurveTo(2.62, 0.86, 2.0, 0.95);
  s.lineTo(1.7, 0.95);
  s.closePath();
  const g = new THREE.ExtrudeGeometry(s, {depth: 0.36, bevelEnabled: true, bevelSize: 0.03, bevelThickness: 0.03, bevelSegments: 3, curveSegments: 16});
  const p = g.attributes.position, n = g.attributes.normal;
  for (let i = 0; i < p.count; i++) { // the drawing's x and y become the watch's y and z; it extrudes along x
    p.setXYZ(i, p.getZ(i), p.getX(i), p.getY(i));
    n.setXYZ(i, n.getZ(i), n.getX(i), n.getY(i));
  }
  return g;
}

function bezelMarks(family: string) {
  const size = 2048, c = document.createElement('canvas');
  c.width = c.height = size;
  const x = c.getContext('2d');
  const perCm = size / 2 / 2.28;
  x.translate(size / 2, size / 2);
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  for (let i = 0; i < 60; i++) {
    const long = i % 5 === 0;
    x.save();
    x.rotate((i / 60) * Math.PI * 2);
    x.fillStyle = long ? '#E4E6EA' : '#9A9DA3';
    if (long) {
      x.font = `500 ${0.15 * perCm}px "${family}"`;
      x.fillText(String(i === 0 ? 60 : i), 0, -2.13 * perCm);
    } else {
      x.fillRect(-0.008 * perCm, -2.22 * perCm, 0.016 * perCm, 0.1 * perCm);
    }
    x.restore();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  return t;
}

export type Shot = {
  cam: Cam;
  draw: (c: CanvasRenderingContext2D) => void; // what's on the screen
  level?: number; // how much light is on the watch, 0 to 1
  glow?: string; // the screen's colour on the case
  glowPower?: number;
  bezel?: number; // degrees the bezel has turned
  sweep?: number; // moves the studio lights' reflections across the metal
  screen?: number; // the screen's brightness, 0 to 1
};

export class Stage {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(FOV, W / H, 0.1, 200);
  faceContext: CanvasRenderingContext2D;
  faceTexture: THREE.CanvasTexture;
  screenMaterial: THREE.MeshBasicMaterial;
  bezel = new THREE.Group();
  watch = new THREE.Group();
  key = new THREE.DirectionalLight(0xfff4ea, 1);
  rim = new THREE.DirectionalLight(0xffffff, 1);
  fill = new THREE.HemisphereLight(0xffffff, 0x20242c, 1);
  glow = new THREE.PointLight(0xffffff, 0, 14, 2);
  drawFace: any;
  glass: THREE.MeshStandardMaterial;
  drawSessions: any;

  constructor(drawFace: any, drawSessions: any, family: string) {
    this.drawFace = drawFace;
    this.drawSessions = drawSessions;
    const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, preserveDrawingBuffer: true});
    renderer.setPixelRatio(2);
    renderer.setSize(W, H, false);
    renderer.setClearColor(0x000000, 0);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer = renderer;

    // A dark studio with long light panels, which is what makes black steel look expensive
    const studio = new THREE.Scene();
    studio.background = new THREE.Color(0x030304);
    const panel = (w: number, h: number, pos: number[], power: number) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({color: new THREE.Color(power, power, power), side: THREE.DoubleSide}));
      m.position.set(pos[0], pos[1], pos[2]);
      m.lookAt(0, 0, 0);
      studio.add(m);
    };
    panel(30, 5, [0, 20, 6], 16);
    panel(4, 34, [-22, 0, 8], 20);
    panel(3, 34, [22, 2, 4], 12);
    panel(26, 3, [0, -20, 8], 6);
    panel(10, 10, [6, 8, 24], 1.2);
    this.scene.environment = new THREE.PMREMGenerator(renderer).fromScene(studio, 0.012).texture;

    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 450 * SCALE;
    this.faceContext = canvas.getContext('2d');
    this.faceTexture = new THREE.CanvasTexture(canvas);
    this.faceTexture.colorSpace = THREE.SRGBColorSpace;
    this.faceTexture.anisotropy = 16;

    const steel = new THREE.MeshStandardMaterial({color: 0x34353a, metalness: 1, roughness: 0.3, side: THREE.DoubleSide});
    const polished = new THREE.MeshStandardMaterial({color: 0x3b3c42, metalness: 1, roughness: 0.17, side: THREE.DoubleSide});

    this.watch.add(lathe([[0, 0.05], [1.8, 0.05], [2.05, 0.16], [2.24, 0.42], [2.27, 0.72], [2.25, 0.78]], steel));
    this.bezel.add(lathe([[2.25, 0.76], [2.33, 0.79], [2.36, 0.84], [2.36, 1.06], [2.31, 1.13], [2.26, 1.145], [1.97, 1.145], [1.91, 1.02], [1.88, 0.99]], polished));
    const ridge = new THREE.InstancedMesh(new THREE.BoxGeometry(0.05, 0.075, 0.2), polished, 120);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < 120; i++) { // the rotating bezel's grip
      const a = (i / 120) * Math.PI * 2;
      dummy.position.set(Math.cos(a) * 2.36, Math.sin(a) * 2.36, 0.95);
      dummy.rotation.set(0, 0, a);
      dummy.updateMatrix();
      ridge.setMatrixAt(i, dummy.matrix);
    }
    ridge.castShadow = true;
    this.bezel.add(ridge);
    const decal = new THREE.Mesh(new THREE.RingGeometry(1.97, 2.26, 256, 1), new THREE.MeshStandardMaterial({map: bezelMarks(family), transparent: true, metalness: 0.2, roughness: 0.5, depthWrite: false}));
    (decal.geometry as THREE.BufferGeometry).attributes.uv.needsUpdate = true;
    // The ring's coordinates run to its outer edge at 2.26; the drawing was made to 2.28
    const uv = decal.geometry.attributes.uv, pos = decal.geometry.attributes.position;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / 2.28 / 2 + 0.5, pos.getY(i) / 2.28 / 2 + 0.5);
    decal.position.z = 1.149;
    this.bezel.add(decal);
    this.watch.add(this.bezel);

    const lug = lugGeometry();
    for (const [x, turn] of [[1.03, 0], [-1.39, 0], [1.03, 1], [-1.39, 1]]) {
      const m = new THREE.Mesh(lug, steel);
      m.castShadow = true;
      const holder = new THREE.Group();
      m.position.x = x;
      holder.add(m);
      holder.rotation.z = turn * Math.PI;
      this.watch.add(holder);
    }
    for (const a of [24, -24]) { // the two buttons, towards the hand
      const b = new THREE.Mesh(new THREE.CapsuleGeometry(0.11, 0.2, 4, 16), steel);
      b.rotation.set(0, 0, Math.PI / 2);
      b.position.set(2.3, 0, 0.42);
      const holder = new THREE.Group();
      holder.add(b);
      holder.rotation.z = (a * Math.PI) / 180;
      this.watch.add(holder);
    }

    const black = new THREE.Mesh(new THREE.CircleGeometry(1.92, 160), new THREE.MeshStandardMaterial({color: 0x020203, roughness: 0.3}));
    black.position.z = 0.97;
    this.watch.add(black);
    this.screenMaterial = new THREE.MeshBasicMaterial({map: this.faceTexture, toneMapped: false});
    const screen = new THREE.Mesh(new THREE.CircleGeometry(1.78, 256), this.screenMaterial);
    screen.position.z = 0.975;
    this.watch.add(screen);
    // The glass only adds reflections: black, so it has no colour of its own, and blended by adding
    const glass = new THREE.Mesh(new THREE.CircleGeometry(1.9, 160), new THREE.MeshStandardMaterial({
      color: 0x000000, metalness: 0, roughness: 0.05, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    glass.position.z = 0.985;
    this.watch.add(glass);
    this.glass = glass.material as THREE.MeshStandardMaterial;

    const strap = new THREE.Mesh(strapGeometry(), new THREE.MeshStandardMaterial({color: 0x0f0f11, roughness: 0.78, metalness: 0}));
    strap.castShadow = true;
    strap.receiveShadow = true;
    this.watch.add(strap);

    this.key.position.set(-6, 10, 14);
    this.key.castShadow = true;
    this.key.shadow.mapSize.set(2048, 2048);
    Object.assign(this.key.shadow.camera, {left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 40});
    this.key.shadow.bias = -0.0004;
    this.key.shadow.normalBias = 0.02;
    this.key.shadow.radius = 5;
    this.rim.position.set(7, 8, -7);
    this.glow.position.set(0, 0, 0.95); // under the glass, so it leaves no glint on it
    this.watch.add(this.glow);
    this.scene.add(this.watch, this.key, this.rim, this.fill);
  }

  /** Draws one picture; returns where the screen's centre landed and its scale. */
  render(s: Shot) {
    const level = s.level ?? 1;
    s.draw(this.faceContext);
    this.faceTexture.needsUpdate = true;
    const brightness = s.screen ?? 1;
    this.screenMaterial.color.setRGB(brightness, brightness, brightness);
    this.bezel.rotation.z = ((s.bezel ?? 0) * Math.PI) / 180;
    this.key.intensity = 1.5 * level;
    this.rim.intensity = 1.6 * level;
    this.fill.intensity = 0.14 * level;
    this.scene.environmentIntensity = 0.85 * level;
    this.scene.environmentRotation.set(0, ((s.sweep ?? 0) * Math.PI) / 180, 0);
    const far = Math.min(1, Math.max(0, (s.cam.dist - 5) / 5));
    this.glass.opacity = 0.8 * far * far; // additive, so this scales the reflection itself
    this.glow.color.set(s.glow ?? '#000000');
    this.glow.intensity = 5 * (s.glowPower ?? 1) * brightness;

    const c = s.cam, yaw = (c.yaw * Math.PI) / 180, pitch = (c.pitch * Math.PI) / 180, roll = (c.roll * Math.PI) / 180;
    const z = 0.975;
    this.camera.position.set(c.px + c.dist * Math.sin(yaw) * Math.cos(pitch), c.py + c.dist * Math.sin(pitch), z + c.dist * Math.cos(yaw) * Math.cos(pitch));
    this.camera.up.set(Math.sin(roll), Math.cos(roll), 0);
    this.camera.lookAt(c.px, c.py, z);
    this.camera.updateMatrixWorld();
    this.renderer.render(this.scene, this.camera);
    const centre = new THREE.Vector3(0, 0, z).project(this.camera);
    return {x: (centre.x * 0.5 + 0.5) * W, y: (-centre.y * 0.5 + 0.5) * H, scale: pxPerCm(c.dist)};
  }
}

let stage: Promise<Stage> | null = null;
export function getStage() {
  if (!stage) {
    stage = (async () => {
      const {fontFamily, waitUntilDone} = loadRoboto('normal', {weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext']});
      await waitUntilDone();
      const {drawFace, drawSessions} = await loadFace(staticFile('face'), fontFamily);
      return new Stage(drawFace, drawSessions, fontFamily);
    })();
  }
  return stage;
}
