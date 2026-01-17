from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)
@app.route("/scan_ip", methods=["POST"])
def scan_ip_post():
    data = request.json
    if not data or "ip" not in data:
        return jsonify({"error": "No IP provided"}), 400

    ip = data["ip"]
    return jsonify({"status": "ok", "ip": ip})

HTML = """
<!doctype html>
<html>
<head>
    <title>NEXUS IP SCANNER</title>
    
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
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { background:#0d1117; color:#c9d1d9; font-family: monospace; padding:20px }
        input, button { padding:5px; margin:5px; font-size:16px }
        table { border-collapse: collapse; margin-top:10px; width:100% }
        th, td { border:1px solid #58a6ff; padding:5px; text-align:left }
        th { background:#161b22 }
        h2 { color:#58a6ff }
        #map { height:400px; margin-top:20px; border-radius:10px; }
    </style>
</head>
<body>
<h1>🖥 NEXUS IP SCANNER</h1>

<div>
    <input type="text" id="ip" placeholder="Enter IP">
    <button onclick="scanIP()">Scan</button>
</div>

<div id="results"></div>
<div id="map"></div>

<script>
let map = L.map('map').setView([20,0],2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom:18 }).addTo(map);

let markers = [];

async function scanIP(){
    let ip = document.getElementById("ip").value;
    if(!ip) return;
    let resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "<p>Scanning...</p>";

    try{
        let r = await fetch("/scan?ip=" + encodeURIComponent(ip));
        let data = await r.json();
        let html = "";

        // Убираем старые маркеры
        for(let m of markers) map.removeLayer(m);
        markers = [];

        for(let source of Object.keys(data)){
            let fields = data[source];
            html += `<h2>${source}</h2><table><tr><th>Field</th><th>Value</th></tr>`;
            for(let [k,v] of Object.entries(fields)){
                html += `<tr><td>${k}</td><td>${JSON.stringify(v)}</td></tr>`;
            }
            html += "</table>";

            // Пытаемся найти координаты для этого сервиса
            let lat = fields.lat || fields.latitude;
            let lon = fields.lon || fields.longitude;
            if(lat && lon){
                let marker = L.circleMarker([lat, lon], {radius:8, color:'lime', fillColor:'lime', fillOpacity:0.7}).addTo(map);
                let popup = `<b>IP:</b> ${ip}<br><b>Service:</b> ${source}<br>`;
                for(let [k,v] of Object.entries(fields)){
                    popup += `${k}: ${JSON.stringify(v)}<br>`;
                }
                marker.bindPopup(popup);
                markers.push(marker);
            }
        }

        resultsDiv.innerHTML = html;

        // Если есть хотя бы один маркер, центрируем на первом
        if(markers.length>0){
            map.setView(markers[0].getLatLng(),4);
        }

    }catch(e){
        resultsDiv.innerHTML = "<p style='color:red'>Error: "+e+"</p>";
    }
}
const params = new URLSearchParams(window.location.search);
const autoIP = params.get("ip");

if(autoIP){
    document.getElementById("ip").value = autoIP;
    scanIP();
}
</script>
</body>
</html>
"""

# OSINT источники
SOURCES = {
    "ipinfo.io": "https://ipinfo.io/{ip}",
    "ipwho.is": "https://ipwho.is/{ip}?security=1",
    "ip2location.io": "https://api.ip2location.io/?ip={ip}",
    "ip-api.com": "http://ip-api.com/json/{ip}?fields=66846719",
    "ipwhois.io": "https://ipwhois.app/json/{ip}",
    "ipapi.co": "https://ipapi.co/{ip}/json/",
    "api.db-ip.com": "https://api.db-ip.com/v2/free/{ip}"
}

# Все ключи
KEYS = [
    "ip","ipAddress","query","version","network",
    "city","city_name",
    "region","regionName","region_name","stateProv","stateProvCode","region_code","district",
    "country","countryName","country_name",
    "country_code","countryCode","country_code_iso3",
    "continent","continentName","continent_code","continentCode",
    "latitude","longitude","lat","lon","loc",
    "postal","zip","zip_code",
    "timezone","timezone_name","utc_offset","offset","timezone_dstOffset","timezone_gmtOffset","timezone_gmt",
    "in_eu","country_tld",
    "org","as","isp","asn","asname","domain","hostname","reverse",
    "calling_code","country_calling_code","country_flag","flag","anycast","country_phone",
    "currency","currency_name","currency_code","currency_symbol","currency_plural",
    "languages",
    "mobile","proxy","hosting","success","type","message","readme","current_time","country_area",
    "country_population","borders","capital","is_eu","currency_rates"
]

def extract_keys(data):
    result = {}
    for key in KEYS:
        if key in data:
            result[key] = data[key]
        else:
            for sub in ["connection","timezone","flag"]:
                if sub in data and key in data[sub]:
                    result[key] = data[sub][key]
    return result

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/scan")
def scan():
    ip = request.args.get("ip")
    if not ip:
        return jsonify({"error":"No IP provided"})

    results = {}
    for name, url_template in SOURCES.items():
        url = url_template.format(ip=ip)
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            try:
                data = r.json()
            except:
                data = {"raw": r.text}
            results[name] = extract_keys(data)
        except Exception as e:
            results[name] = {"error": str(e)}

    return jsonify(results)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=3335)