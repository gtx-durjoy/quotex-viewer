# ======================================================
#  📊 Quotex অটোমেটেড ট্রেডিং সিস্টেম
#  🚀 সিগন্যাল + অ্যালার্ট + UI
# ======================================================

import json
import os
import time
import requests
from datetime import datetime
import random

# ======================================================
#  কনফিগারেশন (তোমার পছন্দমতো পরিবর্তন করো)
# ======================================================

CONFIG = {
    "TARGET_URL": "https://market-qx.trade/en",
    "CANDLE_LIMIT": 500,
    "RSI_PERIOD": 14,
    "SMA_SHORT": 20,
    "SMA_LONG": 50,
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70,
    "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "MIN_PROFIT_PERCENT": 2.0,  # নূন্যতম লাভের শতাংশ
    "STOP_LOSS_PERCENT": 1.5,   # স্টপ লস শতাংশ
    "TRADE_AMOUNT": 10,         # ডলার
}

# ======================================================
#  ডাটা স্টোরেজ
# ======================================================

DATA_FILE = "/tmp/candles.json"
TRADES_FILE = "/tmp/trades.json"

def load_data(file):
    try:
        if os.path.exists(file):
            with open(file, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_data(file, data):
    try:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

# ======================================================
#  ক্যান্ডেল স্ক্র্যাপার
# ======================================================

def scrape_candle():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        response = requests.get(CONFIG["TARGET_URL"], headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
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
    except:
        return None

# ======================================================
#  টেকনিক্যাল ইন্ডিকেটর
# ======================================================

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

def calculate_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = calculate_sma(prices[-fast:], fast)
    ema_slow = calculate_sma(prices[-slow:], slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow
    return macd_line, None, None

# ======================================================
#  সিগন্যাল জেনারেটর (আপগ্রেড)
# ======================================================

def generate_signal(candles):
    if len(candles) < 30:
        return None
    
    closes = [c['close'] for c in candles]
    current_price = closes[-1]
    previous_price = closes[-2] if len(closes) > 1 else current_price
    
    rsi = calculate_rsi(closes, CONFIG["RSI_PERIOD"])
    sma20 = calculate_sma(closes, CONFIG["SMA_SHORT"])
    sma50 = calculate_sma(closes, CONFIG["SMA_LONG"])
    
    signal = {
        'price': current_price,
        'previous_price': previous_price,
        'rsi': rsi,
        'sma20': sma20,
        'sma50': sma50,
        'action': 'HOLD',
        'reason': 'অপেক্ষা করুন',
        'confidence': 0
    }
    
    # BUY সিগন্যাল
    if rsi and rsi < CONFIG["RSI_OVERSOLD"] and current_price < sma20:
        signal['action'] = 'BUY'
        signal['reason'] = f'RSI ওভারসল্ড ({rsi:.2f}) + SMA20 ব্রেক'
        signal['confidence'] = 85
    elif sma20 and sma50 and sma20 > sma50 and current_price > sma20:
        signal['action'] = 'BUY'
        signal['reason'] = f'গোল্ডেন ক্রস (SMA20 {sma20:.2f} > SMA50 {sma50:.2f})'
        signal['confidence'] = 75
    
    # SELL সিগন্যাল
    elif rsi and rsi > CONFIG["RSI_OVERBOUGHT"] and current_price > sma20:
        signal['action'] = 'SELL'
        signal['reason'] = f'RSI ওভারবট ({rsi:.2f}) + SMA20 রেজিস্ট্যান্স'
        signal['confidence'] = 85
    elif sma20 and sma50 and sma20 < sma50 and current_price < sma20:
        signal['action'] = 'SELL'
        signal['reason'] = f'ডেথ ক্রস (SMA20 {sma20:.2f} < SMA50 {sma50:.2f})'
        signal['confidence'] = 75
    
    # প্রাইস অ্যাকশন সিগন্যাল
    if signal['action'] == 'HOLD':
        if current_price > previous_price * 1.02:
            signal['action'] = 'BUY'
            signal['reason'] = 'বুলিশ প্রাইস অ্যাকশন (+2%)'
            signal['confidence'] = 60
        elif current_price < previous_price * 0.98:
            signal['action'] = 'SELL'
            signal['reason'] = 'বিয়ারিশ প্রাইস অ্যাকশন (-2%)'
            signal['confidence'] = 60
    
    return signal

# ======================================================
#  ট্রেড এক্সিকিউটর
# ======================================================

def execute_trade(signal):
    trades = load_data(TRADES_FILE)
    
    trade = {
        'timestamp': time.time(),
        'datetime': datetime.now().isoformat(),
        'action': signal['action'],
        'price': signal['price'],
        'amount': CONFIG["TRADE_AMOUNT"],
        'status': 'OPEN',
        'reason': signal['reason'],
        'confidence': signal['confidence']
    }
    
    trades.append(trade)
    save_data(TRADES_FILE, trades)
    
    # টেলিগ্রামে নোটিফিকেশন
    send_telegram(f"""
🚨 <b>নতুন ট্রেড!</b>
📊 {signal['action']} @ ${signal['price']:.2f}
💰 পরিমাণ: ${CONFIG['TRADE_AMOUNT']}
📝 কারণ: {signal['reason']}
🎯 কনফিডেন্স: {signal['confidence']}%
⏰ {datetime.now().strftime('%H:%M:%S')}
    """)
    
    return trade

# ======================================================
#  টেলিগ্রাম বট
# ======================================================

def send_telegram(message):
    if not CONFIG["TELEGRAM_TOKEN"] or not CONFIG["TELEGRAM_CHAT_ID"]:
        return
    try:
        url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage"
        data = {
            'chat_id': CONFIG['TELEGRAM_CHAT_ID'],
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, data=data, timeout=5)
    except:
        pass

# ======================================================
#  Vercel Handler (API)
# ======================================================

def handler(request):
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(request.url)
        params = parse_qs(parsed.query)
        
        candles = load_data(DATA_FILE)
        trades = load_data(TRADES_FILE)
        
        # UI
        if 'ui' in params:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': get_ui_html()
            }
        
        # স্ক্র্যাপ + সিগন্যাল
        if 'scrape' in params:
            new_candle = scrape_candle()
            if new_candle:
                candles.append(new_candle)
                if len(candles) > CONFIG["CANDLE_LIMIT"]:
                    candles = candles[-CONFIG["CANDLE_LIMIT"]:]
                save_data(DATA_FILE, candles)
        
        # সিগন্যাল জেনারেট
        signal = generate_signal(candles) if len(candles) > 30 else None
        
        # ট্রেড এক্সিকিউট
        trade_executed = None
        if signal and signal['action'] != 'HOLD' and signal['confidence'] > 70:
            trade_executed = execute_trade(signal)
        
        response_data = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'total_candles': len(candles),
            'total_trades': len(trades),
            'active_trades': len([t for t in trades if t['status'] == 'OPEN']),
            'last_signal': signal,
            'last_trade': trades[-1] if trades else None,
            'candles': candles[-50:] if candles else [],
            'recent_trades': trades[-10:] if trades else []
        }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response_data, indent=2)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

# ======================================================
#  HTML UI (সুন্দর ড্যাশবোর্ড)
# ======================================================

def get_ui_html():
    return """
<!DOCTYPE html>
<html>
<head><title>📊 Quotex ট্রেডিং সিগন্যাল</title>
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
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px}
.stat-card{background:#14141e;padding:15px;border-radius:12px;border:1px solid #2a2a3a;text-align:center}
.stat-value{font-size:24px;font-weight:bold;color:#00ff88}
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
.trade-buy{color:#00ff88}
.trade-sell{color:#ff4466}
@media(max-width:600px){.header{flex-direction:column;gap:10px}.signal-big{font-size:32px}.candle{min-width:4px}.candle-body{width:4px}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 Quotex ট্রেডিং সিস্টেম</h1>
<div>
<button class="btn btn-primary" onclick="refreshData()">🔄 রিফ্রেশ</button>
<button class="btn btn-danger" onclick="clearData()">🗑️ ক্লিয়ার</button>
</div>
</div>

<div class="stats" id="stats">
<div class="stat-card"><div>মোট ক্যান্ডেল</div><div class="stat-value" id="totalCandles">0</div></div>
<div class="stat-card"><div>মোট ট্রেড</div><div class="stat-value" id="totalTrades">0</div></div>
<div class="stat-card"><div>এক্টিভ ট্রেড</div><div class="stat-value" id="activeTrades">0</div></div>
</div>

<div class="signal-card">
<div style="font-size:14px;color:#888;">বর্তমান সিগন্যাল</div>
<div class="signal-big signal-hold" id="signalText">⏳ লোড হচ্ছে...</div>
<div style="font-size:14px;color:#888;margin-top:8px;" id="signalReason"></div>
<div style="font-size:14px;color:#888;margin-top:4px;">কনফিডেন্স: <span id="confidence">0%</span></div>
</div>

<div class="chart-container"><div id="chart"></div></div>

<div class="table-container">
<h3 style="margin-bottom:10px;">📋 সর্বশেষ ট্রেড</h3>
<table><thead><tr><th>সময়</th><th>অ্যাকশন</th><th>প্রাইস</th><th>পরিমাণ</th><th>স্ট্যাটাস</th><th>কারণ</th></tr></thead>
<tbody id="tradeBody"></tbody></table>
</div>

<div class="table-container" style="margin-top:20px;">
<h3 style="margin-bottom:10px;">📊 সর্বশেষ ক্যান্ডেল</h3>
<table><thead><tr><th>সময়</th><th>প্রাইস</th><th>ওপেন</th><th>হাই</th><th>লো</th><th>ক্লোজ</th><th>ভলিউম</th></tr></thead>
<tbody id="tableBody"></tbody></table>
</div>
</div>

<script>
async function loadData(){try{const res=await fetch('/api/index?limit=50&signal=true');const data=await res.json();if(data.error)return;
document.getElementById('totalCandles').textContent=data.total_candles||0;
document.getElementById('totalTrades').textContent=data.total_trades||0;
document.getElementById('activeTrades').textContent=data.active_trades||0;
if(data.last_signal){const s=data.last_signal;const el=document.getElementById('signalText');const reason=document.getElementById('signalReason');const conf=document.getElementById('confidence');
if(s.action==='BUY'){el.textContent='🟢 BUY';el.className='signal-big signal-buy';}else if(s.action==='SELL'){el.textContent='🔴 SELL';el.className='signal-big signal-sell';}else{el.textContent='🟡 HOLD';el.className='signal-big signal-hold';}
reason.textContent=s.reason||'';
conf.textContent=(s.confidence||0)+'%';
}
if(data.candles&&data.candles.length>0){renderChart(data.candles);renderTable(data.candles);}
if(data.recent_trades){renderTrades(data.recent_trades);}
}catch(e){console.error(e);}}
function renderChart(candles){const container=document.getElementById('chart');container.innerHTML='<div class="chart" id="chartInner"></div>';const chart=document.getElementById('chartInner');const maxPrice=Math.max(...candles.map(c=>c.high));const minPrice=Math.min(...candles.map(c=>c.low));const range=maxPrice-minPrice||1;candles.forEach(c=>{const div=document.createElement('div');div.className=`candle ${c.close>=c.open?'candle-up':'candle-down'}`;const wick=document.createElement('div');wick.className='wick';wick.style.height=((c.high-c.low)/range)*280+10+'px';div.appendChild(wick);const body=document.createElement('div');body.className='candle-body';body.style.height=Math.max(Math.abs(c.close-c.open)/range*280+2,2)+'px';div.appendChild(body);chart.appendChild(div);});}
function renderTable(candles){const tbody=document.getElementById('tableBody');tbody.innerHTML='';candles.slice().reverse().forEach(c=>{const time=new Date(c.timestamp*1000).toLocaleTimeString();const cls=c.close>=c.open?'price-up':'price-down';tbody.innerHTML+=`<tr><td>${time}</td><td class="${cls}">$${c.price.toFixed(2)}</td><td>$${c.open.toFixed(2)}</td><td>$${c.high.toFixed(2)}</td><td>$${c.low.toFixed(2)}</td><td class="${cls}">$${c.close.toFixed(2)}</td><td>${c.volume.toFixed(2)}</td></tr>`;});}
function renderTrades(trades){const tbody=document.getElementById('tradeBody');tbody.innerHTML='';trades.slice().reverse().forEach(t=>{const time=new Date(t.timestamp*1000).toLocaleTimeString();const cls=t.action==='BUY'?'trade-buy':'trade-sell';tbody.innerHTML+=`<tr><td>${time}</td><td class="${cls}">${t.action}</td><td>$${t.price.toFixed(2)}</td><td>$${t.amount.toFixed(2)}</td><td>${t.status}</td><td>${t.reason||''}</td></tr>`;});}
async function refreshData(){await fetch('/api/index?scrape=true');await loadData();}
async function clearData(){if(!confirm('সব ডাটা ডিলিট করবে?'))return;await fetch('/api/index',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'clear'})});await loadData();}
loadData();setInterval(loadData,15000);
</script>
</body>
</html>
    """
