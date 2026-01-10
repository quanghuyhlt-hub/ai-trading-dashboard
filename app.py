"""
Stock Screener for Vietnamese Stock Market
Quét cổ phiếu trên HOSE, HNX, UPCOM theo các điều kiện kỹ thuật
Author: Expert Python Developer
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import vnstock
try:
    from vnstock import *
    print("✓ VNStock đã được cài đặt và sẵn sàng sử dụng")
except ImportError:
    print("✗ Vui lòng cài đặt vnstock: pip install vnstock")
    exit()

class VietnamStockScreener:
    def __init__(self):
        """Khởi tạo screener với các tham số mặc định"""
        self.results = []
        self.all_symbols = []
        self.today = datetime.now().strftime('%Y-%m-%d')
        
        # Tính ngày bắt đầu cho dữ liệu lịch sử (100 ngày giao dịch)
        self.start_date = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d')
        self.end_date = self.today
        
    def get_all_stock_symbols(self):
        """Lấy toàn bộ mã cổ phiếu trên 3 sàn HOSE, HNX, UPCOM"""
        print("🔄 Đang lấy danh sách mã cổ phiếu...")
        
        try:
            # Lấy toàn bộ danh sách cổ phiếu
            df_listing = listing_companies()
            
            if df_listing is not None and not df_listing.empty:
                # Lọc các mã cổ phiếu đang giao dịch
                self.all_symbols = df_listing['ticker'].tolist()
                print(f"✓ Đã lấy được {len(self.all_symbols)} mã cổ phiếu")
                return True
            else:
                # Fallback: sử dụng danh sách cứng nếu API không hoạt động
                print("⚠ API listing không trả về dữ liệu, sử dụng danh sách mẫu...")
                self.all_symbols = ['VIC', 'VNM', 'VHM', 'HPG', 'SSI', 'MWG', 
                                   'FPT', 'VCB', 'TCB', 'ACB', 'MBB', 'CTG',
                                   'VND', 'HVN', 'PLX', 'GAS', 'POW', 'SAB']
                return True
                
        except Exception as e:
            print(f"✗ Lỗi khi lấy danh sách mã: {e}")
            # Fallback to sample symbols
            self.all_symbols = ['VIC', 'VNM', 'VHM', 'HPG', 'SSI', 'MWG']
            return False
    
    def calculate_technical_indicators(self, df):
        """Tính toán các chỉ báo kỹ thuật từ dữ liệu lịch sử"""
        if len(df) < 50:
            return None
            
        # Tạo bản sao để tránh cảnh báo SettingWithCopyWarning
        df = df.copy()
        
        # Tính MA20 và MA50
        df['MA20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['MA50'] = df['close'].rolling(window=50, min_periods=1).mean()
        
        # Tính trung bình volume 20 ngày
        df['AvgVolume20'] = df['volume'].rolling(window=20, min_periods=1).mean()
        
        # Tính % change
        df['pct_change'] = df['close'].pct_change() * 100
        
        return df
    
    def check_condition_1(self, df):
        """
        Điều kiện 1: MA20 chuẩn bị cắt lên MA50 hoặc đã cắt trong 3 phiên gần nhất
        Trả về True nếu thỏa mãn và thông tin chi tiết
        """
        if len(df) < 3:
            return False, ""
            
        # Lấy dữ liệu 5 phiên gần nhất để kiểm tra
        recent_data = df.tail(5).reset_index(drop=True)
        
        # Kiểm tra điểm cắt
        for i in range(len(recent_data)-1, max(len(recent_data)-4, 0), -1):
            if i < 1:
                continue
                
            # Kiểm tra MA20 đã cắt lên MA50
            current_ma20 = recent_data.loc[i, 'MA20']
            current_ma50 = recent_data.loc[i, 'MA50']
            prev_ma20 = recent_data.loc[i-1, 'MA20']
            prev_ma50 = recent_data.loc[i-1, 'MA50']
            
            # Điều kiện cắt lên: MA20 hiện tại > MA50 và trước đó <=
            if current_ma20 > current_ma50 and prev_ma20 <= prev_ma50:
                days_ago = len(recent_data) - i - 1
                if days_ago == 0:
                    return True, "MA20 vừa cắt lên MA50 (hôm nay)"
                else:
                    return True, f"MA20 cắt lên MA50 ({days_ago} phiên trước)"
        
        # Kiểm tra chuẩn bị cắt (MA20 đang tiến gần MA50 từ dưới lên)
        latest_ma20 = recent_data.iloc[-1]['MA20']
        latest_ma50 = recent_data.iloc[-1]['MA50']
        prev_ma20 = recent_data.iloc[-2]['MA20']
        prev_ma50 = recent_data.iloc[-2]['MA50']
        
        # MA20 đang tăng và tiến gần MA50 (cách dưới 2%)
        if (latest_ma20 < latest_ma50 and 
            latest_ma20 > prev_ma20 and 
            latest_ma50 - latest_ma20 < latest_ma50 * 0.02):
            return True, "MA20 chuẩn bị cắt lên MA50 (cách <2%)"
        
        return False, ""
    
    def check_condition_2(self, df, realtime_volume):
        """
        Điều kiện 2: Volume surge - volume hôm nay > 120% trung bình 20 ngày
        """
        if len(df) < 21:
            return False, ""
            
        # Lấy trung bình volume 20 ngày (không tính hôm nay)
        avg_volume_20 = df.iloc[:-1]['AvgVolume20'].iloc[-1]
        
        if avg_volume_20 == 0:
            return False, ""
            
        volume_ratio = realtime_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        volume_pct = (volume_ratio - 1) * 100
        
        if volume_ratio > 1.2:
            return True, f"Volume tăng {volume_pct:.1f}% vs TB20"
        
        return False, ""
    
    def check_condition_3(self, df, current_price):
        """
        Điều kiện 3: Flat base pattern - đi nền trong 40 phiên
        """
        if len(df) < 40:
            return False, ""
            
        # Lấy dữ liệu 40 phiên gần nhất
        base_data = df.tail(40).copy()
        
        # Tính các giá trị cần thiết
        highest_high = base_data['high'].max()
        lowest_low = base_data['low'].min()
        avg_close = base_data['close'].mean()
        
        if avg_close == 0:
            return False, ""
            
        # Tính biên độ (%)
        amplitude = (highest_high - lowest_low) / avg_close * 100
        
        # Tính điểm giữa của base
        base_midpoint = (highest_high + lowest_low) / 2
        
        # Điều kiện flat base: biên độ ≤ 12% và giá hiện tại ở nửa trên
        if amplitude <= 12 and current_price >= base_midpoint:
            position_pct = (current_price - lowest_low) / (highest_high - lowest_low) * 100
            return True, f"Flat base {amplitude:.1f}%, vị trí {position_pct:.1f}%"
        
        return False, ""
    
    def get_realtime_data(self, symbol):
        """Lấy dữ liệu thời gian thực cho một mã cổ phiếu"""
        try:
            # Lấy quote thời gian thực
            quote = stock_quote(symbol)
            
            if quote is not None and not quote.empty:
                # Chuyển đổi cột thành chữ thường để truy cập dễ dàng
                quote.columns = [col.lower() for col in quote.columns]
                
                # Lấy giá và volume
                current_price = quote.loc[0, 'price'] if 'price' in quote.columns else quote.loc[0, 'close']
                price_change = quote.loc[0, 'percent_change'] if 'percent_change' in quote.columns else 0
                volume = quote.loc[0, 'volume'] if 'volume' in quote.columns else 0
                
                return {
                    'price': float(current_price),
                    'change_pct': float(price_change),
                    'volume': int(volume)
                }
        except Exception as e:
            print(f"  ⚠ Lỗi khi lấy realtime data cho {symbol}: {e}")
        
        # Fallback: trả về dữ liệu từ lịch sử nếu realtime thất bại
        return None
    
    def scan_stock(self, symbol):
        """Quét một mã cổ phiếu cụ thể"""
        try:
            print(f"  📊 Đang phân tích {symbol}...", end='\r')
            
            # Lấy dữ liệu lịch sử
            df = stock_historical_data(
                symbol=symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                resolution='1D'
            )
            
            if df is None or df.empty or len(df) < 50:
                return None
            
            # Tính chỉ báo kỹ thuật
            df = self.calculate_technical_indicators(df)
            if df is None:
                return None
            
            # Lấy dữ liệu thời gian thực
            realtime_data = self.get_realtime_data(symbol)
            if realtime_data is None:
                # Sử dụng dữ liệu từ ngày giao dịch gần nhất
                latest = df.iloc[-1]
                current_price = latest['close']
                current_volume = latest['volume']
                change_pct = latest['pct_change']
            else:
                current_price = realtime_data['price']
                current_volume = realtime_data['volume']
                change_pct = realtime_data['change_pct']
            
            # Kiểm tra các điều kiện
            cond1_result, cond1_note = self.check_condition_1(df)
            cond2_result, cond2_note = self.check_condition_2(df, current_volume)
            cond3_result, cond3_note = self.check_condition_3(df, current_price)
            
            # Chỉ thêm vào kết quả nếu thỏa ít nhất 1 điều kiện
            if cond1_result or cond2_result or cond3_result:
                # Xác định sàn giao dịch
                exchange = "HOSE"  # Mặc định, có thể cải thiện bằng API
                if symbol.endswith('.HN'):
                    exchange = "HNX"
                elif symbol.endswith('.UP'):
                    exchange = "UPCOM"
                
                # Tạo ghi chú kết hợp
                conditions_met = []
                notes = []
                
                if cond1_result:
                    conditions_met.append("MA20 Cross")
                    notes.append(cond1_note)
                if cond2_result:
                    conditions_met.append("Volume Surge")
                    notes.append(cond2_note)
                if cond3_result:
                    conditions_met.append("Flat Base")
                    notes.append(cond3_note)
                
                # Tính volume ratio
                avg_volume_20 = df.iloc[:-1]['AvgVolume20'].iloc[-1] if len(df) > 20 else 0
                volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
                
                return {
                    'Symbol': symbol,
                    'Exchange': exchange,
                    'Price': current_price,
                    '% Change': change_pct,
                    'Volume': current_volume,
                    'Volume vs Avg20': f"{volume_ratio:.2f}x",
                    'Conditions Met': ', '.join(conditions_met),
                    'Note': ' | '.join(notes)
                }
            
            return None
            
        except Exception as e:
            print(f"  ✗ Lỗi khi quét {symbol}: {e}")
            return None
    
    def run_screener(self, max_stocks=None):
        """Chạy screener trên toàn bộ danh sách mã cổ phiếu"""
        print("\n" + "="*80)
        print("🚀 BẮT ĐẦU QUÉT CỔ PHIẾU VIỆT NAM")
        print("="*80)
        
        # Lấy danh sách mã cổ phiếu
        if not self.get_all_stock_symbols():
            return
        
        # Giới hạn số lượng mã nếu cần (cho test)
        if max_stocks and len(self.all_symbols) > max_stocks:
            symbols_to_scan = self.all_symbols[:max_stocks]
            print(f"\n⚠ Chế độ test: chỉ quét {max_stocks} mã đầu tiên")
        else:
            symbols_to_scan = self.all_symbols
        
        # Quét từng mã
        self.results = []
        total_symbols = len(symbols_to_scan)
        
        print(f"\n🔍 Đang quét {total_symbols} mã cổ phiếu...")
        
        for i, symbol in enumerate(symbols_to_scan, 1):
            # Hiển thị tiến độ
            progress = (i / total_symbols) * 100
            print(f"  📈 Tiến độ: {i}/{total_symbols} ({progress:.1f}%) - Đang xử lý {symbol}", end='\r')
            
            # Quét mã
            result = self.scan_stock(symbol)
            if result:
                self.results.append(result)
        
        print("\n" + "="*80)
        print(f"✅ HOÀN TẤT: Tìm thấy {len(self.results)} mã thỏa điều kiện")
        print("="*80)
        
        return self.results
    
    def display_results(self):
        """Hiển thị kết quả dưới dạng DataFrame"""
        if not self.results:
            print("Không tìm thấy mã nào thỏa điều kiện!")
            return None
        
        # Tạo DataFrame từ kết quả
        df_results = pd.DataFrame(self.results)
        
        # Sắp xếp theo Volume giảm dần
        df_results = df_results.sort_values(by='Volume', ascending=False)
        
        # Định dạng cột
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 30)
        
        print("\n📋 KẾT QUẢ QUÉT CỔ PHIẾU:")
        print("-" * 120)
        print(df_results.to_string(index=False))
        print("-" * 120)
        
        # Thống kê
        print(f"\n📊 THỐNG KÊ:")
        print(f"  • Tổng số mã thỏa điều kiện: {len(df_results)}")
        print(f"  • Phân bổ theo sàn:")
        if 'Exchange' in df_results.columns:
            print(df_results['Exchange'].value_counts().to_string())
        
        # Phân bổ theo điều kiện
        conditions_count = {}
        for conditions in df_results['Conditions Met']:
            for cond in conditions.split(', '):
                conditions_count[cond] = conditions_count.get(cond, 0) + 1
        
        print(f"\n  • Phân bổ theo điều kiện:")
        for cond, count in conditions_count.items():
            print(f"    - {cond}: {count} mã")
        
        return df_results
    
    def save_to_csv(self, filename=None):
        """Lưu kết quả ra file CSV"""
        if not self.results:
            print("Không có dữ liệu để lưu!")
            return
        
        if filename is None:
            filename = f"stock_screener_results_{self.today}.csv"
        
        df_results = pd.DataFrame(self.results)
        df_results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 Đã lưu kết quả vào file: {filename}")
        
        return filename
    
    def refresh_scan(self):
        """Làm mới và chạy lại screener"""
        print("\n🔄 Đang làm mới dữ liệu và quét lại...")
        self.results = []
        return self.run_screener()


# Hàm chính để chạy screener
def main():
    """Hàm chạy chính của chương trình"""
    # Tạo screener
    screener = VietnamStockScreener()
    
    # Chạy screener (có thể giới hạn số lượng mã cho test)
    # Để quét toàn bộ, bỏ tham số max_stocks hoặc đặt thành None
    screener.run_screener(max_stocks=50)  # Test với 50 mã đầu tiên
    
    # Hiển thị kết quả
    results_df = screener.display_results()
    
    # Lưu kết quả ra CSV
    if results_df is not None and not results_df.empty:
        screener.save_to_csv()
    
    return screener


# Hàm để chạy nhanh trong Jupyter Notebook
def run_quick_scan(symbols=None, max_stocks=20):
    """
    Chạy quét nhanh với danh sách mã cụ thể hoặc số lượng giới hạn
    
    Parameters:
    -----------
    symbols : list
        Danh sách mã cổ phiếu cụ thể cần quét
    max_stocks : int
        Số lượng mã tối đa cần quét
    """
    screener = VietnamStockScreener()
    
    if symbols:
        screener.all_symbols = symbols
    else:
        screener.get_all_stock_symbols()
        if max_stocks and len(screener.all_symbols) > max_stocks:
            screener.all_symbols = screener.all_symbols[:max_stocks]
    
    print(f"🔍 Quét nhanh {len(screener.all_symbols)} mã cổ phiếu...")
    
    for symbol in screener.all_symbols:
        result = screener.scan_stock(symbol)
        if result:
            screener.results.append(result)
    
    if screener.results:
        df = pd.DataFrame(screener.results)
        df = df.sort_values(by='Volume', ascending=False)
        print(f"\n✅ Tìm thấy {len(df)} mã thỏa điều kiện:")
        print(df.to_string(index=False))
        return df
    else:
        print("❌ Không tìm thấy mã nào thỏa điều kiện!")
        return None


if __name__ == "__main__":
    # Chạy screener đầy đủ khi thực thi script
    screener = main()
    
    # Hướng dẫn sử dụng thêm
    print("\n" + "="*80)
    print("💡 HƯỚNG DẪN SỬ DỤNG:")
    print("="*80)
    print("1. Để chạy lại screener: screener.refresh_scan()")
    print("2. Để hiển thị kết quả: screener.display_results()")
    print("3. Để lưu kết quả: screener.save_to_csv('ten_file.csv')")
    print("4. Để quét nhanh 20 mã: run_quick_scan()")
    print("5. Để quét mã cụ thể: run_quick_scan(['VIC', 'VNM', 'HPG'])")
