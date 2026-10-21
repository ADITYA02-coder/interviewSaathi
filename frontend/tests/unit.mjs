import { encodeWav } from "../src/lib/recorder.js";
import { splitSentences } from "../src/lib/speaker.js";
const sr = 48000, tone = new Float32Array(sr).map((_, i) => 0.5 * Math.sin(2 * Math.PI * 440 * i / sr));
const blob = encodeWav([tone.slice(0, 24000), tone.slice(24000)], sr);
const b = Buffer.from(await blob.arrayBuffer());
const rd = (o, n) => b.toString("ascii", o, o + n);
console.log(rd(0,4), rd(8,4), rd(12,4), "rate", b.readUInt32LE(24), "ch", b.readUInt16LE(22), "bits", b.readUInt16LE(34), "bytes", b.length, "(expected", 44 + 16000 * 2, ")");
console.log(splitSentences("Good point. Can a class implement multiple interfaces? How is that different from extending classes?"));
console.log(splitSentences("ठीक है। जावा में इंटरफ़ेस क्या होता है? समझाइए।"));
// API base URL handling for split deployments (Vercel UI + separate API host)
const { wsBase, API_BASE } = await import("../src/lib/api.js");
console.log("same-origin default:", JSON.stringify(API_BASE), "(empty means relative /api)");
