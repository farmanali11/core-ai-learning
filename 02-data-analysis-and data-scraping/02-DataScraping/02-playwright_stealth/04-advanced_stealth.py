"""
advanced_stealth.py
-------------------
Phase 4: Canvas, WebGL, Audio spoofing + Proxy rotation.
Import alongside stealth_factory.py and human_behaviour.py.
"""
import random
import asyncio
from playwright.async_api import BrowserContext

CANVAS_PATCH = """
(function(){
  const nTD = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(t,q){
    const ctx = this.getContext('2d');
    if(ctx){
      const d = ctx.getImageData(0,0,this.width,this.height);
      for(let i=0;i<d.data.length;i+=4){
        d.data[i] = (d.data[i] + 1) & 0xFF;
      }
      ctx.putImageData(d,0,0);
    }
    return nTD.apply(this,arguments);
  };
})();
"""

WEBGL_PATCH_TEMPLATE = """
(function(){
  const P = {{ 'v': "{vendor}", 'r': "{renderer}" }};
  const patch=(ctx)=>{{
    const og=ctx.getParameter.bind(ctx);
    ctx.getParameter=function(p){{
      const e=ctx.getExtension('WEBGL_debug_renderer_info');
      if(e){{
        if(p===e.UNMASKED_VENDOR_WEBGL)   return P.v;
        if(p===e.UNMASKED_RENDERER_WEBGL) return P.r;
      }}
      return og(p);
    }};
  }};
  const og=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(t,a){{
    const c=og.apply(this,arguments);
    if(c&&(t==='webgl'||t==='webgl2'||t==='experimental-webgl'))patch(c);
    return c;
  }};
})();
"""

AUDIO_PATCH = """
(function(){
  const og=AudioBuffer.prototype.getChannelData;
  AudioBuffer.prototype.getChannelData=function(ch){
    const d=og.call(this,ch);
    for(let i=0;i<d.length;i+=100){
      d[i] += (Math.random() - 0.5) * 1e-7;
    }
    return d;
  };
})();
"""

VENDORS = ["Intel Inc.", "NVIDIA Corporation", "ATI Technologies Inc."]
RENDERERS = [
    "Intel(R) Iris(R) Xe Graphics",
    "NVIDIA GeForce RTX 4060/PCIe/SSE2",
    "AMD Radeon(TM) Graphics"
]

async def inject_hardware_spoofing(context: BrowserContext):
    """Injects JS scripts before any page load to mask fingerprints."""
    # 1. Canvas Fingerprint protection
    await context.add_init_script(CANVAS_PATCH)
    
    # 2. WebGL Hardware configuration randomization
    webgl_script = WEBGL_PATCH_TEMPLATE.format(
        vendor=random.choice(VENDORS),
        renderer=random.choice(RENDERERS)
    )
    await context.add_init_script(webgl_script)
    
    # 3. Audio Context Fingerprint protection
    await context.add_init_script(AUDIO_PATCH)


class RotatingProxyManager:
    """Manages pool proxy allocation and simple failure penalties."""
    def __init__(self, proxies: list[dict]):
        self.proxies = proxies
        self._failed = set()

    def get_proxy(self) -> dict | None:
        if not self.proxies: 
            return None
        ok = [p for p in self.proxies if p["server"] not in self._failed]
        pool = ok if ok else self.proxies
        return random.choice(pool)

    def fail(self, proxy: dict): 
        self._failed.add(proxy["server"])
        
    def ok(self,  proxy: dict): 
        self._failed.discard(proxy["server"])
