# ======================================================
#  📡 Quotex ক্যান্ডেল API - Vercel রেডি
#  🚀 সবকিছু এক ফাইলেই (api/index.py)
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
    "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "TARGET_URL": os.environ.get("TARGET_URL", "https://market-qx.trade/en"),
    "CANDLE_LIMIT": 500,
    "RSI_PERIOD": 14,
    "SMA_SHORT": 20,
    "SMA_LONG": 50,
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70,
}

# ======================================================
#  ডাটা স্টোরেজ (Vercel tmp ফোল্ডারে)
# ======================================================

DATA_FILE = "/tmp/candles.json"

def load_candles() -> List[Dict]:
    """ক্যান্ডেল ডাটা লোড করো"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_candles(candles: List[Dict]):
    """ক্যান্ডেল ডাটা সেভ করো"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(candles, f, indent=2)
    except:
        pass

# ======================================================
#  ক্যান্ডেল স্ক্র্যাপার
# ======================================================

def scrape_candle() -> Optional[Dict]:
    """বর্তমান ক্যান্ডেল ডাটা স্ক্র্যাপ করো"""
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
        
        # ⚠️ সাইটের রিয়েল HTML অনুযায়ী আপডেট করো
        # ডেমো ডাটা (রিয়েল সাইটে পরিবর্তন করো)
        import random
        base_price = 100.0 + (time.time() % 20)
        
        candle = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'price': round(base_price, 2),
            'volume': round(random.uniform(0.5, 5.0), 2),
            'open': round(base_price - random.uniform(0, 2), 2),
            'high': round(base_price + random.uniform(0, 3), 2),
            'low': round(base_price - random.uniform(0, 3), 2),
            'close': round(base_price + random.uniform(-2, 2), 2)
        }
        
        return candle
        
    except Exception as e:
        print(f"❌ স্ক্র্যাপিং এরর: {e}")
        return None

# ======================================================
#  টেকনিক্যাল ইন্ডিকেটর
# ======================================================

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """RSI ক্যালকুলেশন"""
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
    """SMA ক্যালকুলেশন"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

# ======================================================
#  সিগন্যাল জেনারেটর
# ======================================================

def generate_signal(candles: List[Dict]) -> Optional[Dict]:
    """ট্রেডিং সিগন্যাল জেনারেট করো"""
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
#  টেলিগ্রাম বট
# ======================================================

def send_telegram_message(message: str) -> bool:
    """টেলিগ্রামে মেসেজ পাঠাও"""
    if not CONFIG["TELEGRAM_TOKEN"] or not CONFIG["TELEGRAM_CHAT_ID"]:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage"
        data = {
            'chat_id': CONFIG['TELEGRAM_CHAT_ID'],
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_candle_alert(candle: Dict):
    """ক্যান্ডেল ডাটা টেলিগ্রামে পাঠাও"""
    message = f"""
📊 <b>নতুন ক্যান্ডেল</b>
⏰ {datetime.fromtimestamp(candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
💰 প্রাইস: ${candle['price']:.2f}
📈 ওপেন: ${candle['open']:.2f}
📉 ক্লোজ: ${candle['close']:.2f}
📊 ভলিউম: {candle['volume']:.2f}
    """
    send_telegram_message(message)

def send_signal_alert(signal: Dict):
    """সিগন্যাল টেলিগ্রামে পাঠাও"""
    emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
    message = f"""
{emoji} <b>{signal['action']} সিগন্যাল!</b>

💰 প্রাইস: ${signal['price']:.2f}
📊 RSI: {signal['rsi']:.2f if signal['rsi'] else 'N/A'}
📈 SMA20: {signal['sma20']:.2f if signal['sma20'] else 'N/A'}
📉 SMA50: {signal['sma50']:.2f if signal['sma50'] else 'N/A'}
📝 কারণ: {signal['reason']}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    send_telegram_message(message)

# ======================================================
#  মেইন API হ্যান্ডলার (Vercel-এর জন্য)
# ======================================================

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """GET রিকোয়েস্ট হ্যান্ডেল করো"""
        try:
            # ক্যান্ডেল ডাটা লোড করো
            candles = load_candles()
            
            # নতুন ক্যান্ডেল স্ক্র্যাপ করো
            new_candle = scrape_candle()
            
            response_data = {
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'total_candles': len(candles)
            }
            
            if new_candle:
                candles.append(new_candle)
                
                # লিমিট মেইনটেইন করো
                if len(candles) > CONFIG["CANDLE_LIMIT"]:
                    candles = candles[-CONFIG["CANDLE_LIMIT"]:]
                
                save_candles(candles)
                
                # টেলিগ্রামে ক্যান্ডেল পাঠাও
                send_candle_alert(new_candle)
                
                # সিগন্যাল চেক করো
                if len(candles) % 5 == 0:
                    signal = generate_signal(candles)
                    if signal and signal['action'] != 'HOLD':
                        send_signal_alert(signal)
                        response_data['signal'] = signal
                
                response_data['latest_candle'] = new_candle
            
            # শেষ ১০টি ক্যান্ডেল দেখাও
            response_data['recent_candles'] = candles[-10:] if candles else []
            
            # JSON রেসপন্স
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
        """POST রিকোয়েস্ট (সিগন্যাল জেনারেট করার জন্য)"""
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
    
    def log_message(self, format, *args):
        """লগ বন্ধ করো (Vercel-এর জন্য)"""
        pass

# ======================================================
#  লোকাল রানের জন্য (Vercel-এ ব্যবহার করবে না)
# ======================================================

if __name__ == "__main__":
    from http.server import HTTPServer
    
    print("🚀 Quotex API লোকাল সার্ভার চালু হচ্ছে...")
    print(f"📡 http://localhost:8080/api/candles")
    
    server = HTTPServer(('0.0.0.0', 8080), handler)
    server.serve_forever()
