from flask import Flask, jsonify, render_template_string
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os
import requests
import ast

LOG_FILE = "ip.log"

app = Flask(__name__)
address_cache = {}  # ключ = (lat, lon), значение = адрес
def get_address(lat, lon):
    key = (round(lat, 6), round(lon, 6))  # округляем для точности
    if key in address_cache:
        return address_cache[key]
    
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        r = requests.get(url, headers={"User-Agent": "NEXUS-IP-STATISTIC"}, timeout=3)
        data = r.json()
        address = data.get("display_name", "-")
    except:
        address = "-"
    
    address_cache[key] = address  # сохраняем в кэш
    return address
        
# --- получение инфы о IP ---
@app.route("/ipinfo/<ip>")
def ipinfo(ip):
    try:
        r = requests.get(f"https://ipwho.is/{ip}?security=1", timeout=5)
        data = r.json()
        # можно добавить проверку смены IP, VPN и прочее
        return jsonify(data)
    except:
        return jsonify({"error": "Не удалось получить данные"})

# --- флаг страны ---
def country_flag(code):
    if not code or len(code) != 2 or not code.isalpha():
        return "🌐"
    code = code.upper()
    return chr(0x1F1E6 + ord(code[0]) - 65) + chr(0x1F1E6 + ord(code[1]) - 65)

# --- парсим лог ---

def parse_log():
    visits = []
    if not os.path.exists(LOG_FILE):
        return visits

    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                time_str = line.split("|")[0].strip()
                t = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

                def extract(key):
                    return line.split(f"{key}:")[1].split("|")[0].strip() if f"{key}:" in line else "-"

                ip = extract("IP")
                country = extract("Country")
                loc = extract("Loc")
                src = extract("SRC")
                ua = extract("UA")

                lat, lon = map(float, loc.split(","))

                # --- HARDWARE ---
                hw = {
                    "platform": extract("Platform"),
                    "cores": extract("Cores"),
                    "ram": extract("RAM"),
                    "touch": extract("Touch"),
                    "timezone": extract("TZ"),
                    "language": extract("Lang"),
                }

                # Screen (dict)
                try:
                    hw["screen"] = ast.literal_eval(extract("Screen"))
                except:
                    hw["screen"] = extract("Screen")

                # GPU (dict)
                try:
                    hw["gpu"] = ast.literal_eval(extract("GPU"))
                except:
                    hw["gpu"] = extract("GPU")

                # --- NETWORK ---
                net = {
                    "type": extract("NetType"),
                    "rtt": extract("RTT"),
                    "down": extract("Down"),
                    "save": extract("SaveData")
                }

                # --- WEBRTC ---
                webrtc = {
                    "ips": extract("WebRTC_IPs"),
                    "local": extract("Local"),
                    "public": extract("Public"),
                    "rtt": extract("RTT"),
                    "bitrate": extract("Bitrate")
                }

                visits.append((t, country, lat, lon, ip, src, ua, hw, net, webrtc))

            except:
                pass

    return visits

HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>NEXUS Dashboard</title>

    <!-- Favicons -->
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='Dashboard/favicon.ico') }}">
    <link rel="icon" type="image/png" sizes="16x16" href="{{ url_for('static', filename='Dashboard/favicon-16x16.png') }}">
    <link rel="icon" type="image/png" sizes="32x32" href="{{ url_for('static', filename='Dashboard/favicon-32x32.png') }}">

    <!-- Apple -->
    <link rel="apple-touch-icon" sizes="180x180" href="{{ url_for('static', filename='Dashboard/apple-touch-icon.png') }}">

    <!-- Android / PWA -->
    <link rel="manifest" href="{{ url_for('static', filename='Dashboard/site.webmanifest') }}">
    <meta name="theme-color" content="#0d1117">

    <!-- Mobile -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { background:#0d1117; color:#c9d1d9; font-family: monospace; padding:20px }
        h1 { color:#58a6ff }
        .box { margin-bottom:30px }
        canvas { background:#161b22; padding:10px; border-radius:10px }
        #map { background:#161b22; margin-top:10px; border-radius:10px; height:400px }
        .btn {
          background:#161b22;
          color:#58a6ff;
          border:1px solid #58a6ff;
          padding:8px 14px;
          font-size:16px;
          cursor:pointer;
          border-radius:6px;
        }
        .btn:hover {
          background:#58a6ff;
          color:#0d1117;
        }
        .sound-btn {
           position: fixed;
           bottom: 20px;
           right: 20px;
           z-index: 9999;

           background: #161b22;
           color: #58a6ff;
           border: 1px solid #58a6ff;
           border-radius: 50%;
           width: 56px;
           height: 56px;

           font-size: 24px;
           cursor: pointer;

           box-shadow: 0 0 10px rgba(88,166,255,0.4);
        }

        .sound-btn:hover {
           background: #58a6ff;
           color: #0d1117;
        }
    </style>
</head>
<body>
<div style="display:flex; align-items:center; padding:10px;">
    <img src="static/Dashboard/NEXUS.png" alt="NEXUS" style="height:90px; margin-right:10px;">
    <h1 style="color:#58a6ff; font-family:monospace;">Dashboard</h1>
</div>

<div class="box">
    <p>👥 Всего визитов: <b id="total">0</b></p>
    <p>🟢 Онлайн (60 сек): <b id="online">0</b></p>
    <button id="scannerBtn" class="btn" class="btn">
        🛰 IP Scanner
    </button>
</div>

<div class="box">
    <h3>Визиты по минутам</h3>
    <canvas id="visits"></canvas>
</div>

<div class="box">
    <h3>Страны</h3>
    <canvas id="countries"></canvas>
</div>

<div class="box">
    <h3>🏆 Top Countries</h3>
    <table id="top" style="width:100%; border-collapse:collapse"></table>
</div>

<div class="box">
    <h3>🌍 Map</h3>
    <div id="map"></div>
</div>
<button id="soundToggle" class="sound-btn">🔇</button>
<audio id="detectSound" src="{{ url_for('static', filename='assets/detect.mp3') }}"></audio>
<script>
let visitsChart, countriesChart;
let map = L.map('map').setView([20,0],2);
let markers = [];
let ipLists = []; // список IP для tooltip

// OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom:18 }).addTo(map);

document.getElementById("scannerBtn").onclick = () => {
    // Определяем текущий хост и протокол
    const host = window.location.hostname; // автоматически IP или домен сервера
    const protocol = window.location.protocol; // http: или https:
    
    // Формируем URL для сервиса на другом порту
    const url = `${protocol}//${host}:3335`; 
    
    // Открываем в новой вкладке
    window.open(url, "_blank");
};

let audioUnlocked = false;
let soundEnabled = false;
const detectSound = document.getElementById("detectSound");
const soundBtn = document.getElementById("soundToggle");

// начальное состояние
soundBtn.textContent = "🔇";
soundBtn.style.background = "#161b22";

soundBtn.onclick = () => {
    if (!audioUnlocked) {
        detectSound.play().then(() => {
            audioUnlocked = true;
            soundEnabled = true;
            soundBtn.textContent = "🔊";
            soundBtn.style.background = "#58a6ff";
        }).catch(e => console.log("[AUDIO] блокировано", e));
    } else {
        soundEnabled = !soundEnabled;
        soundBtn.textContent = soundEnabled ? "🔊" : "🔇";
        soundBtn.style.background = soundEnabled ? "#58a6ff" : "#161b22";
        if (soundEnabled) detectSound.play().catch(e=>console.log(e));
    }
};

function initCharts(){
    visitsChart = new Chart(document.getElementById("visits"), {
        type:"line",
        data: { labels:[], datasets:[{label:"Visits", data:[], borderColor:'lime', backgroundColor:'rgba(0,255,0,0.2)'}] },
        options: { responsive:true, animation:false,
            plugins:{ tooltip:{ callbacks:{
                label: function(context){
                    let index = context.dataIndex;
                    let ips = ipLists[index] || [];
                    return ["Visits: "+context.parsed.y].concat(ips);
                }
            }}}}
    });

    countriesChart = new Chart(document.getElementById("countries"), {
        type:"bar",
        data:{ labels:[], datasets:[{label:"Countries", data:[], backgroundColor:'lime'}] },
        options:{ responsive:true, animation:false }
    });
}

// fetch IP info для цвета и popup
async function fetchIPInfo(ip){
    try{
        let r = await fetch(`/ipinfo/${ip}`);
        return await r.json();
    } catch(e){
        return {"error":"Не удалось получить данные"};
    }
}

let markersDict = {}; // { ip: marker }

async function updateMap(coords){

    for(let c of coords){
        let key = c.ip;
        let isNew = false;

        if(markersDict[key]) {
            let old = markersDict[key];
            if(old.lat !== c.lat || old.lon !== c.lon || old.address !== c.address){
                map.removeLayer(old);
                delete markersDict[key];
                isNew = true; // маркер обновляется → новый визит
            } else {
                continue; // маркер не меняем
            }
        } else {
            isNew = true; // новый IP
        }

        // создаём маркер
        let color = 'lime';
        let marker = L.circleMarker([c.lat, c.lon], {
            radius: 6,
            color: color,
            fillColor: color,
            fillOpacity: 0.7
        }).addTo(map);

        // Пульсирующий эффект
        if(isNew){
            let pulse = L.circle([c.lat, c.lon], {
                radius: 100,
                color: 'lime',
                fillColor: 'lime',
                fillOpacity: 0.3,
                weight: 2
            }).addTo(map);

            let grow = 100;
            let alpha = 0.3;
            let interval = setInterval(()=>{
                grow += 8;
                alpha -= 0.02;
                if(alpha <= 0){
                    map.removeLayer(pulse);
                    clearInterval(interval);
                } else {
                    pulse.setRadius(grow);
                    pulse.setStyle({fillOpacity: alpha, opacity: alpha});
                }
            },50);

            // Воспроизведение звука
            if (soundEnabled) {
               detectSound.currentTime = 0;
          detectSound.play().catch(e=>console.log(e));
            }
        }

        // ТВОЙ оригинальный попап, не трогаем содержимое
        marker.bindPopup(`
            <b>IP:</b> ${c.ip}<br>
            <b>Country:</b> ${c.country || '-'}<br>
            <b>Address:</b> ${c.address || '-'}<br>
            <b>Lat, Lon:</b> ${c.lat}, ${c.lon}<br>
            <b>Geo Source:</b> ${c.src === "GEO" ? "Geolocation" : "IP"}<br>
            <hr>
            <b>Platform:</b> ${c.hw?.platform || '-'}<br>
            <b>CPU cores:</b> ${c.hw?.cores || '-'}<br>
            <b>RAM:</b> ${c.hw?.ram || '-'}<br>
            <b>Screen:</b> ${c.hw?.screen?.w}×${c.hw?.screen?.h} (DPR ${c.hw?.screen?.dpr})<br>
            <b>Touch:</b> ${c.hw?.touch || '-'}<br>
            <b>Timezone:</b> ${c.hw?.timezone || '-'}<br>
            <b>Language:</b> ${c.hw?.language || '-'}<br>
            <b>GPU:</b><br>
            <small>
            ${c.hw?.gpu?.vendor || ''}<br>
            ${c.hw?.gpu?.renderer || ''}
            </small><br>
            <hr>
            <b>Network:</b><br>
            <b>Type:</b> ${c.net?.type || '-'}<br>
            <b>RTT:</b> ${c.net?.rtt || '-'} ms<br>
            <b>Down:</b> ${c.net?.down || '-'} Mb<br>
            <b>SaveData:</b> ${c.net?.save || '-'}<br>
            <hr>
            <b>WebRTC:</b><br>
            <b>IPs:</b> ${c.webrtc?.ips || '-'}<br>
            <b>Local:</b> ${c.webrtc?.local || '-'}<br>
            <b>Public:</b> ${c.webrtc?.public || '-'}<br>
            <b>RTT:</b> ${c.webrtc?.rtt || '-'}<br>
            <b>Bitrate:</b> ${c.webrtc?.bitrate || '-'}<br>
            <hr>
            <b>User-Agent:</b><br>
            <small>${c.ua || '-'}</small>
        `);

        markersDict[key] = marker;
        marker.lat = c.lat;
        marker.lon = c.lon;
        marker.address = c.address;
    }
}

function updateTop(top){
    let html = "";
    top.forEach(c=>{
        html+=`<tr>
            <td style="font-size:22px">${c.flag}</td>
            <td>${c.country}</td>
            <td><b>${c.count}</b></td>
        </tr>`;
    });
    document.getElementById("top").innerHTML = html;
}

function updateStats(){
    fetch("/stats")
    .then(r=>r.json())
    .then(async d=>{
        document.getElementById("total").textContent=d.total;
        document.getElementById("online").textContent=d.online;

        ipLists = d.ip_lists;

        visitsChart.data.labels = d.times;
        visitsChart.data.datasets[0].data = d.counts;
        visitsChart.update();

        countriesChart.data.labels = d.countries_labels;
        countriesChart.data.datasets[0].data = d.countries_counts;
        countriesChart.update();

        await updateMap(d.coords);
        updateTop(d.top);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCharts();        // графики
    updateStats();       // карта + таблицы
    setInterval(updateStats, 2000);
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    visits = parse_log()
    now = datetime.now()
    online = sum(1 for v in visits if now - v[0] < timedelta(seconds=60))
    return render_template_string(HTML, total=len(visits), online=online)

@app.route("/stats")
def stats():
    visits = parse_log()
    now = datetime.now()

    online = sum(1 for t, _, _, _, _, _, _, _, _, _ in visits if now - t < timedelta(seconds=60))

    per_min = defaultdict(list)
    countries = Counter()
    coords = []

    for t,c,lat,lon,ip,src,ua,hw,net,webrtc in visits:   # <-- добавили src
      address = get_address(lat, lon)
      per_min[t.strftime("%H:%M")].append(ip)
      countries[c] += 1
      coords.append({
          "lat": lat,
          "lon": lon,
          "ip": ip,
          "country": c,
          "src": src,  
          "ua": ua,
          "address": address,
          "hw": hw,
          "net": net,
          "webrtc": webrtc
      })

    times = list(per_min.keys())[-20:]
    counts = [len(per_min[k]) for k in times]
    ip_lists = [per_min[k] for k in times]

    top = countries.most_common(10)
    top_list = [{"country":c,"count":n,"flag":country_flag(c)} for c,n in top]

    return jsonify({
        "total":len(visits),
        "online":online,
        "times":times,
        "counts":counts,
        "ip_lists":ip_lists,
        "coords":coords,
        "top":top_list,
        "countries_labels":list(countries.keys()),
        "countries_counts":list(countries.values())
    })

if __name__=="__main__":
    app.run(host="0.0.0.0", port=3334)