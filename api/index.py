# ======================================================
#  📡 Quotex ক্যান্ডেল API (Vercel রেডি)
#  🚀 টেলিগ্রাম ছাড়া - শুধু JSON ডাটা
# ======================================================

import json
import os
import time
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from typing import List, Dict, Optional

# ======================================================
#  কনফিগারেশন
# ======================================================

CONFIG = {
    "TARGET_URL": os.environ.get("TARGET_URL", "https://market-qx.trade/en"),
    "CANDLE_LIMIT": 500,
    "RSI_PERIOD": 14,
    "SMA_SHORT": 20,
    "SMA_LONG": 50,
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70,
}

DATA_FILE = "/tmp/candles.json"

# ======================================================
#  ডাটা স্টোরেজ
# ======================================================

def load_candles() -> List[Dict]:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_candles(candles: List[Dict]):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(candles, f, indent=2)
    except:
        pass

# ======================================================
#  ক্যান্ডেল স্ক্র্যাপার
# ======================================================

def scrape_candle() -> Optional[Dict]:
    """সাইট থেকে ক্যান্ডেল ডাটা নিয়ে আসো"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'no-cache'
        }
        
        response = requests.get(CONFIG["TARGET_URL"], headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        # ⚠️ ডেমো ডাটা - রিয়েল সাইটের HTML অনুযায়ী পরিবর্তন করো
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
        print(f"❌ স্ক্র্যাপিং এরর: {e}")
        return None

# ======================================================
#  টেকনিক্যাল ইন্ডিকেটর
# ======================================================

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
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

def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

# ======================================================
#  সিগন্যাল জেনারেটর
# ======================================================

def generate_signal(candles: List[Dict]) -> Optional[Dict]:
    if len(candles) < 20:
        return None
    
    closes = [c['close'] for c in candles]
    current_price = closes[-1]
    
    rsi = calculate_rsi(closes, CONFIG["RSI_PERIOD"])
    sma20 = calculate_sma(closes, CONFIG["SMA_SHORT"])
    sma50 = calculate_sma(closes, CONFIG["SMA_LONG"])
    
    signal = {
        'price': current_price,
        'rsi': rsi,
        'sma20': sma20,
        'sma50': sma50,
        'action': 'HOLD',
        'reason': 'না'
    }
    
    if rsi and rsi < CONFIG["RSI_OVERSOLD"]:
        signal['action'] = 'BUY'
        signal['reason'] = f'RSI ওভারসল্ড ({rsi:.2f})'
    elif rsi and rsi > CONFIG["RSI_OVERBOUGHT"]:
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
#  API হ্যান্ডলার
# ======================================================

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            candles = load_candles()
            
            # ক্যোয়ারি প্যারামিটার পার্স করো
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            # যদি HTML চায়, তাহলে UI পাঠাও
            if 'ui' in params:
                self.send_ui()
                return
            
            # নতুন ক্যান্ডেল স্ক্র্যাপ করো
            new_candle = scrape_candle()
            
            response_data = {
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'total_candles': len(candles)
            }
            
            if new_candle:
                candles.append(new_candle)
                if len(candles) > CONFIG["CANDLE_LIMIT"]:
                    candles = candles[-CONFIG["CANDLE_LIMIT"]:]
                save_candles(candles)
                response_data['latest_candle'] = new_candle
            
            # লিমিট প্যারামিটার
            limit = int(params.get('limit', [10])[0])
            response_data['candles'] = candles[-limit:] if candles else []
            
            # সিগন্যাল
            if 'signal' in params:
                signal = generate_signal(candles)
                response_data['signal'] = signal if signal else {'action': 'HOLD', 'reason': 'পর্যাপ্ত ডাটা নেই'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
            
            action = post_data.get('action', '')
            candles = load_candles()
            
            if action == 'signal':
                signal = generate_signal(candles)
                response = {
                    'status': 'success',
                    'signal': signal if signal else {'action': 'HOLD', 'reason': 'পর্যাপ্ত ডাটা নেই'}
                }
            elif action == 'clear':
                save_candles([])
                response = {'status': 'success', 'message': 'ডাটা ক্লিয়ার করা হয়েছে'}
            else:
                response = {
                    'status': 'error',
                    'message': 'অজানা অ্যাকশন। signal বা clear ব্যবহার করো'
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def send_ui(self):
        """সুন্দর UI HTML পাঠাও"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>📊 Quotex ক্যান্ডেল ভিউয়ার</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0f;
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: auto; }
        
        /* হেডার */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: #14141e;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #2a2a3a;
        }
        .header h1 { color: #00ff88; font-size: 28px; }
        .header .status {
            padding: 8px 16px;
            background: #00ff88;
            color: #000;
            border-radius: 20px;
            font-weight: bold;
        }
        
        /* সিগন্যাল কার্ড */
        .signal-card {
            background: #14141e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 2px solid #2a2a3a;
            text-align: center;
        }
        .signal-card .signal-big {
            font-size: 48px;
            font-weight: bold;
        }
        .signal-buy { color: #00ff88; }
        .signal-sell { color: #ff4466; }
        .signal-hold { color: #ffaa00; }
        
        /* চার্ট */
        .chart-container {
            background: #14141e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #2a2a3a;
            overflow-x: auto;
        }
        .chart {
            display: flex;
            align-items: flex-end;
            height: 300px;
            gap: 2px;
        }
        .candle {
            min-width: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
        }
        .candle-body {
            width: 8px;
            border-radius: 2px;
            min-height: 2px;
        }
        .candle-up .candle-body { background: #00ff88; }
        .candle-down .candle-body { background: #ff4466; }
        .candle .wick {
            width: 2px;
            background: #888;
            margin: 0 auto;
        }
        
        /* টেবিল */
        .table-container {
            background: #14141e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a3a;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #1a1a2e;
            color: #888;
            font-weight: 600;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #1a1a2e;
        }
        .price-up { color: #00ff88; }
        .price-down { color: #ff4466; }
        
        /* বাটন */
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            background: #2a2a3a;
            color: #e0e0e0;
        }
        .btn:hover { transform: scale(1.05); }
        .btn-primary { background: #00ff88; color: #000; }
        .btn-danger { background: #ff4466; color: #fff; }
        
        /* রেস্পন্সিভ */
        @media (max-width: 600px) {
            .header { flex-direction: column; gap: 10px; text-align: center; }
            .signal-card .signal-big { font-size: 32px; }
            .candle { min-width: 4px; }
            .candle-body { width: 4px; }
        }
    </style>
</head>
<body>
<div class="container">
    <!-- হেডার -->
    <div class="header">
        <h1>📊 Quotex ক্যান্ডেল</h1>
        <div>
            <span class="status" id="status">● লাইভ</span>
            <button class="btn btn-danger" onclick="clearData()" style="margin-left:10px;">🗑️ ক্লিয়ার</button>
            <button class="btn btn-primary" onclick="refreshData()" style="margin-left:10px;">🔄 রিফ্রেশ</button>
        </div>
    </div>
    
    <!-- সিগন্যাল -->
    <div class="signal-card" id="signalCard">
        <div style="font-size:14px;color:#888;">বর্তমান সিগন্যাল</div>
        <div class="signal-big signal-hold" id="signalText">⏳ লোড হচ্ছে...</div>
        <div style="font-size:14px;color:#888;margin-top:8px;" id="signalReason"></div>
    </div>
    
    <!-- চার্ট -->
    <div class="chart-container">
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span>📈 ক্যান্ডেল চার্ট</span>
            <span id="chartInfo">লোড হচ্ছে...</span>
        </div>
        <div class="chart" id="chart"></div>
    </div>
    
    <!-- টেবিল -->
    <div class="table-container">
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span>📋 সর্বশেষ ক্যান্ডেল</span>
            <span id="tableInfo"></span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>সময়</th>
                    <th>প্রাইস</th>
                    <th>ওপেন</th>
                    <th>হাই</th>
                    <th>লো</th>
                    <th>ক্লোজ</th>
                    <th>ভলিউম</th>
                </tr>
            </thead>
            <tbody id="tableBody"></tbody>
        </table>
    </div>
</div>

<script>
    // ==============================================
    //  ডাটা লোড করা
    // ==============================================
    
    async function loadData() {
        try {
            const response = await fetch('/api/index?limit=50&signal=true');
            const data = await response.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }
            
            // সিগন্যাল আপডেট
            if (data.signal) {
                const signal = data.signal;
                const el = document.getElementById('signalText');
                const reason = document.getElementById('signalReason');
                
                if (signal.action === 'BUY') {
                    el.textContent = '🟢 BUY';
                    el.className = 'signal-big signal-buy';
                    reason.textContent = signal.reason;
                } else if (signal.action === 'SELL') {
                    el.textContent = '🔴 SELL';
                    el.className = 'signal-big signal-sell';
                    reason.textContent = signal.reason;
                } else {
                    el.textContent = '🟡 HOLD';
                    el.className = 'signal-big signal-hold';
                    reason.textContent = 'কোনো সিগন্যাল নেই';
                }
            }
            
            // চার্ট আপডেট
            if (data.candles && data.candles.length > 0) {
                renderChart(data.candles);
                renderTable(data.candles);
                document.getElementById('chartInfo').textContent = 
                    `শেষ ${data.candles.length} টি ক্যান্ডেল | ${new Date(data.timestamp).toLocaleString()}`;
                document.getElementById('tableInfo').textContent = 
                    `${data.total_candles} টি মোট ক্যান্ডেল`;
            }
            
            // স্ট্যাটাস
            document.getElementById('status').textContent = data.latest_candle ? '● লাইভ' : '● অফলাইন';
            
        } catch (error) {
            console.error('ডাটা লোড করতে পারিনি:', error);
        }
    }
    
    // ==============================================
    //  চার্ট রেন্ডার
    // ==============================================
    
    function renderChart(candles) {
        const container = document.getElementById('chart');
        container.innerHTML = '';
        
        const maxPrice = Math.max(...candles.map(c => c.high));
        const minPrice = Math.min(...candles.map(c => c.low));
        const range = maxPrice - minPrice || 1;
        
        candles.forEach(candle => {
            const div = document.createElement('div');
            div.className = `candle ${candle.close >= candle.open ? 'candle-up' : 'candle-down'}`;
            
            // উইক (হাই-লো)
            const wick = document.createElement('div');
            wick.className = 'wick';
            const wickHeight = ((candle.high - candle.low) / range) * 280 + 10;
            wick.style.height = wickHeight + 'px';
            div.appendChild(wick);
            
            // বডি (ওপেন-ক্লোজ)
            const body = document.createElement('div');
            body.className = 'candle-body';
            const bodyHeight = Math.abs(candle.close - candle.open) / range * 280 + 2;
            body.style.height = Math.max(bodyHeight, 2) + 'px';
            div.appendChild(body);
            
            container.appendChild(div);
        });
    }
    
    // ==============================================
    //  টেবিল রেন্ডার
    // ==============================================
    
    function renderTable(candles) {
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';
        
        candles.slice().reverse().forEach(c => {
            const tr = document.createElement('tr');
            const time = new Date(c.timestamp * 1000).toLocaleTimeString();
            const priceClass = c.close >= c.open ? 'price-up' : 'price-down';
            
            tr.innerHTML = `
                <td>${time}</td>
                <td class="${priceClass}">$${c.price.toFixed(2)}</td>
                <td>$${c.open.toFixed(2)}</td>
                <td>$${c.high.toFixed(2)}</td>
                <td>$${c.low.toFixed(2)}</td>
                <td class="${priceClass}">$${c.close.toFixed(2)}</td>
                <td>${c.volume.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    // ==============================================
    //  একশন
    // ==============================================
    
    async function refreshData() {
        document.getElementById('status').textContent = '⏳ লোড...';
        await loadData();
    }
    
    async function clearData() {
        if (!confirm('সব ডাটা ডিলিট করবে?')) return;
        try {
            await fetch('/api/index', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'clear' })
            });
            await loadData();
        } catch (error) {
            console.error(error);
        }
    }
    
    // ==============================================
    //  অটো রিফ্রেশ (প্রতি ১০ সেকেন্ডে)
    // ==============================================
    
    loadData();
    setInterval(loadData, 10000);
</script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

# ======================================================
#  লোকাল রানের জন্য
# ======================================================

if __name__ == "__main__":
    from http.server import HTTPServer
    print("🚀 Quotex ভিউয়ার লোকাল সার্ভার চালু হচ্ছে...")
    print("📡 http://localhost:8080/api/index?ui")
    server = HTTPServer(('0.0.0.0', 8080), handler)
    server.serve_forever()
