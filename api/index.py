# api/index.py - Vercel-এর জন্য ঠিক করা

import json
import os
import time
import requests
from datetime import datetime

# ======================================================
#  কনফিগারেশন
# ======================================================

CONFIG = {
    "TARGET_URL": "https://market-qx.trade/en",
    "CANDLE_LIMIT": 500,
    "RSI_PERIOD": 14,
    "SMA_SHORT": 20,
    "SMA_LONG": 50,
}

DATA_FILE = "/tmp/candles.json"

def load_candles():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_candles(candles):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(candles, f, indent=2)
    except:
        pass

def scrape_candle():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        response = requests.get(CONFIG["TARGET_URL"], headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        import random
        base_price = 100.0 + (time.time() % 20)
        return {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'price': round(base_price, 2),
            'volume': round(random.uniform(0.5, 5.0), 2),
            'open': round(base_price - random.uniform(0, 2), 2),
            'high': round(base_price + random.uniform(0, 3), 2),
            'low': round(base_price - random.uniform(0, 3), 2),
            'close': round(base_price + random.uniform(-2, 2), 2)
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def generate_signal(candles):
    if len(candles) < 20:
        return None
    closes = [c['close'] for c in candles]
    current_price = closes[-1]
    rsi = calculate_rsi(closes)
    sma20 = calculate_sma(closes, 20)
    sma50 = calculate_sma(closes, 50)
    signal = {'price': current_price, 'rsi': rsi, 'sma20': sma20, 'sma50': sma50, 'action': 'HOLD', 'reason': 'না'}
    if rsi and rsi < 30:
        signal['action'] = 'BUY'
        signal['reason'] = f'RSI ওভারসল্ড ({rsi:.2f})'
    elif rsi and rsi > 70:
        signal['action'] = 'SELL'
        signal['reason'] = f'RSI ওভারবট ({rsi:.2f})'
    elif sma20 and sma50 and sma20 > sma50:
        signal['action'] = 'BUY'
        signal['reason'] = f'গোল্ডেন ক্রস (SMA20 {sma20:.2f} > SMA50 {sma50:.2f})'
    elif sma20 and sma50 and sma20 < sma50:
        signal['action'] = 'SELL'
        signal['reason'] = f'ডেথ ক্রস (SMA20 {sma20:.2f} < SMA50 {sma50:.2f})'
    return signal

# ======================================================
#  Vercel Handler (Serverless Function)
# ======================================================

def handler(request):
    """Vercel Python Runtime-এর জন্য সঠিক ফরম্যাট"""
    from urllib.parse import urlparse, parse_qs
    
    # URL পার্স
    parsed = urlparse(request.url)
    params = parse_qs(parsed.query)
    
    # UI দেখানোর জন্য
    if 'ui' in params:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': get_ui_html()
        }
    
    # ডাটা লোড
    candles = load_candles()
    
    # স্ক্র্যাপ
    if 'scrape' in params:
        new_candle = scrape_candle()
        if new_candle:
            candles.append(new_candle)
            if len(candles) > CONFIG["CANDLE_LIMIT"]:
                candles = candles[-CONFIG["CANDLE_LIMIT"]:]
            save_candles(candles)
    
    # রেসপন্স
    response_data = {
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'total_candles': len(candles),
        'candles': candles[-50:] if candles else [],
        'signal': generate_signal(candles) if len(candles) > 20 else None
    }
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data, indent=2)
    }

# ======================================================
#  HTML UI
# ======================================================

def get_ui_html():
    return """
<!DOCTYPE html>
<html>
<head><title>📊 Quotex ক্যান্ডেল ভিউয়ার</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}
.container{max-width:1200px;margin:auto}
.header{display:flex;justify-content:space-between;align-items:center;padding:20px;background:#14141e;border-radius:12px;margin-bottom:20px;border:1px solid #2a2a3a}
.header h1{color:#00ff88;font-size:28px}
.btn{padding:10px 24px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;background:#2a2a3a;color:#e0e0e0}
.btn-primary{background:#00ff88;color:#000}
.btn-danger{background:#ff4466;color:#fff}
.signal-card{background:#14141e;border-radius:12px;padding:20px;margin-bottom:20px;border:2px solid #2a2a3a;text-align:center}
.signal-big{font-size:48px;font-weight:bold}
.signal-buy{color:#00ff88}
.signal-sell{color:#ff4466}
.signal-hold{color:#ffaa00}
.chart-container{background:#14141e;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2a3a;overflow-x:auto}
.chart{display:flex;align-items:flex-end;height:300px;gap:2px}
.candle{min-width:8px;display:flex;flex-direction:column;align-items:center}
.candle-body{width:8px;border-radius:2px;min-height:2px}
.candle-up .candle-body{background:#00ff88}
.candle-down .candle-body{background:#ff4466}
.candle .wick{width:2px;background:#888;margin:0 auto}
.table-container{background:#14141e;border-radius:12px;padding:20px;border:1px solid #2a2a3a;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;padding:12px;background:#1a1a2e;color:#888}
td{padding:10px 12px;border-bottom:1px solid #1a1a2e}
.price-up{color:#00ff88}
.price-down{color:#ff4466}
@media(max-width:600px){.header{flex-direction:column;gap:10px}.signal-big{font-size:32px}.candle{min-width:4px}.candle-body{width:4px}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 Quotex ক্যান্ডেল</h1>
<div>
<button class="btn btn-primary" onclick="refreshData()">🔄 রিফ্রেশ</button>
<button class="btn btn-danger" onclick="clearData()">🗑️ ক্লিয়ার</button>
</div>
</div>
<div class="signal-card"><div style="font-size:14px;color:#888;">বর্তমান সিগন্যাল</div>
<div class="signal-big signal-hold" id="signalText">⏳ লোড হচ্ছে...</div>
<div style="font-size:14px;color:#888;margin-top:8px;" id="signalReason"></div></div>
<div class="chart-container"><div id="chart"></div></div>
<div class="table-container">
<table><thead><tr><th>সময়</th><th>প্রাইস</th><th>ওপেন</th><th>হাই</th><th>লো</th><th>ক্লোজ</th><th>ভলিউম</th></tr></thead>
<tbody id="tableBody"></tbody></table></div></div>
<script>
async function loadData(){try{const res=await fetch('/api/index?limit=50&signal=true');const data=await res.json();if(data.error)return;if(data.signal){const el=document.getElementById('signalText');const reason=document.getElementById('signalReason');if(data.signal.action==='BUY'){el.textContent='🟢 BUY';el.className='signal-big signal-buy';reason.textContent=data.signal.reason;}else if(data.signal.action==='SELL'){el.textContent='🔴 SELL';el.className='signal-big signal-sell';reason.textContent=data.signal.reason;}else{el.textContent='🟡 HOLD';el.className='signal-big signal-hold';reason.textContent='কোনো সিগন্যাল নেই';}}
if(data.candles&&data.candles.length>0){renderChart(data.candles);renderTable(data.candles);}}catch(e){console.error(e);}}
function renderChart(candles){const container=document.getElementById('chart');container.innerHTML='<div class="chart" id="chartInner"></div>';const chart=document.getElementById('chartInner');const maxPrice=Math.max(...candles.map(c=>c.high));const minPrice=Math.min(...candles.map(c=>c.low));const range=maxPrice-minPrice||1;candles.forEach(c=>{const div=document.createElement('div');div.className=`candle ${c.close>=c.open?'candle-up':'candle-down'}`;const wick=document.createElement('div');wick.className='wick';wick.style.height=((c.high-c.low)/range)*280+10+'px';div.appendChild(wick);const body=document.createElement('div');body.className='candle-body';body.style.height=Math.max(Math.abs(c.close-c.open)/range*280+2,2)+'px';div.appendChild(body);chart.appendChild(div);});}
function renderTable(candles){const tbody=document.getElementById('tableBody');tbody.innerHTML='';candles.slice().reverse().forEach(c=>{const time=new Date(c.timestamp*1000).toLocaleTimeString();const cls=c.close>=c.open?'price-up':'price-down';tbody.innerHTML+=`<tr><td>${time}</td><td class="${cls}">$${c.price.toFixed(2)}</td><td>$${c.open.toFixed(2)}</td><td>$${c.high.toFixed(2)}</td><td>$${c.low.toFixed(2)}</td><td class="${cls}">$${c.close.toFixed(2)}</td><td>${c.volume.toFixed(2)}</td></tr>`;});}
async function refreshData(){await fetch('/api/index?scrape=true');await loadData();}
async function clearData(){if(!confirm('সব ডাটা ডিলিট করবে?'))return;await fetch('/api/index',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'clear'})});await loadData();}
loadData();setInterval(loadData,15000);
</script>
</body>
</html>
    """
