import logging
import requests
import pytz
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CẤU HÌNH ---
TELEGRAM_BOT_TOKEN = '7759170307:AAGRfrebGT7wxi7BYxRvw-AjykerhoHWhfI'  # Token của bạn
TELEGRAM_CHAT_ID = '5882369573'  # THAY BẰNG CHAT ID CỦA BẠN
DAILY_REPORT_HOUR = 8  # Giờ gửi báo cáo hàng ngày (24h format)
DAILY_REPORT_MINUTE = 1  # Phút gửi báo cáo hàng ngày

# --- CẤU HÌNH API CAFEF ---
CURRENT_PRICE_API_URL = 'https://cafef.vn/du-lieu/Ajax/ajaxgoldprice.ashx'
RING_HISTORY_API_URL = 'https://cafef.vn/du-lieu/Ajax/AjaxGoldPriceRing.ashx'
TARGET_GOLD_NAME = "NHẪN TRƠN PNJ 999.9"  # Mục tiêu theo dõi

REGIONS = {"hcm": "00", "hanoi": "11"}
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Referer': 'https://cafef.vn/',
}
VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CÁC HÀM LẤY DỮ LIỆU ---

def get_pnj_ring_price():
    """Hàm chuyên dụng để lấy giá Nhẫn Trơn PNJ từ API CafeF."""
    params = {'index': REGIONS["hanoi"]}
    try:
        response = requests.get(CURRENT_PRICE_API_URL, params=params, headers=API_HEADERS)
        response.raise_for_status()
        price_list = response.json().get('Data', [])
        
        for item in price_list:
            if item.get('name', '').upper() == TARGET_GOLD_NAME:
                # Chia cho 10 để chuyển từ triệu đồng/lượng sang triệu đồng/chỉ
                buy_price_per_chi = item.get('buyPrice', 0) / 1000  # 100 (original division) * 10 (tael to chi)
                sell_price_per_chi = item.get('sellPrice', 0) / 1000 # 100 (original division) * 10 (tael to chi)
                logger.info(f"Tìm thấy giá {TARGET_GOLD_NAME}: Mua {buy_price_per_chi:.2f}, Bán {sell_price_per_chi:.2f}")
                return {
                    "buy": buy_price_per_chi,
                    "sell": sell_price_per_chi
                }
        logger.warning(f"Không tìm thấy '{TARGET_GOLD_NAME}' trong dữ liệu API.")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy giá Nhẫn PNJ: {e}")
        return None

def get_ring_price_history():
    """Lấy dữ liệu lịch sử giá vàng nhẫn cho lệnh /t."""
    params = {'zone': REGIONS["hanoi"], 'time': '1m'}
    try:
        response = requests.get(RING_HISTORY_API_URL, params=params, headers=API_HEADERS)
        response.raise_for_status()
        return response.json().get("Data", {}).get("goldPriceWorldHistories", [])
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu lịch sử vàng nhẫn: {e}")
        return None

# --- CÁC LỆNH (HANDLER) ---

async def command_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /n - Chỉ hiển thị giá Nhẫn Trơn PNJ."""
    logger.info(f"Nhận lệnh /n từ user {update.effective_user.id}")
    await update.message.reply_text(f"Đang lấy giá {TARGET_GOLD_NAME} tại Hà Nội, vui lòng chờ...")
    
    price = get_pnj_ring_price()
    
    if price:
        message = (
            f"**{TARGET_GOLD_NAME} (Hà Nội)**\n"
            f"------------------------------------\n"
            f"Mua vào: **{price['buy']:.2f}**\n"
            f"Bán ra: **{price['sell']:.2f}**\n"
            f"_Đơn vị: triệu đồng/chỉ_" # Đã thay đổi đơn vị
        )
        await update.message.reply_markdown(message)
    else:
        await update.message.reply_text("Không thể lấy được giá vàng vào lúc này.")

async def command_thirty_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /t - Báo cáo lịch sử giá vàng nhẫn."""
    logger.info(f"Nhận lệnh /t từ user {update.effective_user.id}")
    await update.message.reply_text("Đang tổng hợp báo cáo giá Vàng Nhẫn Trơn PNJ 30 ngày...")
    history = get_ring_price_history()
    if not history:
        await update.message.reply_text("Không thể lấy được dữ liệu lịch sử.")
        return
    report_lines = [f"📊 **Báo cáo giá Nhẫn Trơn PNJ 999.9 (Hà Nội) - Đơn vị: triệu đồng/chỉ** 📊\n"] # Đã thay đổi đơn vị
    for item in history:
        try:
            date_str = datetime.fromisoformat(item['lastUpdated'].replace(' ', 'T')).strftime('%d/%m')
            # Chia cho 10 để chuyển từ triệu đồng/lượng sang triệu đồng/chỉ
            buy_price = f"{item.get('buyPrice', 0) / 1000:.2f}" # 100 (original division) * 10 (tael to chi)
            sell_price = f"{item.get('sellPrice', 0) / 1000:.2f}" # 100 (original division) * 10 (tael to chi)
            report_lines.append(f"`{date_str}`: Mua **{buy_price}** - Bán **{sell_price}**")
        except (ValueError, KeyError): continue
    full_report = "\n".join(report_lines)
    await update.message.reply_markdown(full_report)

# --- CÔNG VIỆC ĐỊNH KỲ (SCHEDULED JOB) ---

async def job_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gửi báo cáo giá Nhẫn Trơn PNJ hàng ngày vào giờ được cấu hình."""
    current_time = datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Thực hiện job gửi tin lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d} tại {current_time}")
    price = get_pnj_ring_price()
    if price:
        message = (
            f"☀️ **Chào ngày mới! Giá {TARGET_GOLD_NAME} (Hà Nội) lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d}** ☀️\n"
            f"------------------------------------\n"
            f"🔸 **Mua vào:** {price['buy']:.2f} triệu đồng/chỉ\n" # Đã thay đổi đơn vị
            f"🔹 **Bán ra:** {price['sell']:.2f} triệu đồng/chỉ\n\n" # Đã thay đổi đơn vị
            f"Gõ /n để cập nhật."
        )
        try:
            await context.bot.send_message(context.job.chat_id, text=message, parse_mode='HTML')
            logger.info(f"Gửi tin nhắn lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d} thành công đến chat_id {context.job.chat_id}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d}: {e}")
    else:
        error_message = f"Không thể lấy được giá vàng vào lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d}."
        try:
            await context.bot.send_message(context.job.chat_id, text=error_message)
            logger.error(error_message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo lỗi lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d}: {e}")

async def job_check_price_change(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job mới: Kiểm tra giá mỗi 30 phút và thông báo nếu có thay đổi."""
    current_time = datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Thực hiện job kiểm tra giá 30 phút tại {current_time}")
    current_price = get_pnj_ring_price()
    if not current_price:
        logger.warning("Không thể lấy giá vàng, bỏ qua kiểm tra thay đổi giá.")
        try:
            await context.bot.send_message(context.job.chat_id, text="Không thể lấy giá vàng để kiểm tra thay đổi.")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo lỗi kiểm tra giá: {e}")
        return

    previous_price = context.bot_data.get('last_pnj_price', None)
    context.bot_data['last_pnj_price'] = current_price

    if previous_price:
        buy_diff = current_price['buy'] - previous_price['buy']
        sell_diff = current_price['sell'] - previous_price['sell']
        # Chỉ thông báo nếu thay đổi lớn hơn 0.001 triệu đồng (tương đương 0.01 triệu đồng/lượng)
        if abs(buy_diff) >= 0.001 or abs(sell_diff) >= 0.001: # Đã điều chỉnh ngưỡng thay đổi
            logger.info(f"Phát hiện giá thay đổi! Mua: {buy_diff:+.2f}, Bán: {sell_diff:+.2f}")
            buy_arrow = "🔼" if buy_diff > 0 else "🔽" if buy_diff < 0 else "➡️"
            sell_arrow = "🔼" if sell_diff > 0 else "🔽" if sell_diff < 0 else "➡️"
            
            message = (
                f"⚠️ **CẢNH BÁO GIÁ VÀNG NHẪN (HÀ NỘI)** ⚠️\n"
                f"------------------------------------\n"
                f"{buy_arrow} **Mua:** **{current_price['buy']:.2f}** ({buy_diff:+.2f})\n"
                f"   (Trước đó: {previous_price['buy']:.2f})\n"
                f"{sell_arrow} **Bán:** **{current_price['sell']:.2f}** ({sell_diff:+.2f})\n"
                f"   (Trước đó: {previous_price['sell']:.2f})\n"
                f"_Đơn vị: triệu đồng/chỉ_" # Đã thay đổi đơn vị
            )
            try:
                await context.bot.send_message(context.job.chat_id, text=message, parse_mode='Markdown')
                logger.info(f"Gửi thông báo thay đổi giá thành công đến chat_id {context.job.chat_id}")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo thay đổi giá: {e}")

# --- HÀM MAIN ĐỂ CHẠY BOT ---

def main() -> None:
    """Khởi động bot và lên lịch công việc."""
    if TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID' or not TELEGRAM_CHAT_ID.isdigit():
        logger.error("LỖI: TELEGRAM_CHAT_ID chưa được cấu hình. Vui lòng cập nhật TELEGRAM_CHAT_ID.")
        return

    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        job_queue = application.job_queue

        application.add_handler(CommandHandler("n", command_now))
        application.add_handler(CommandHandler("t", command_thirty_days))

        # Lên lịch gửi tin hàng ngày
        current_time = datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Lên lịch job lúc {DAILY_REPORT_HOUR}:{DAILY_REPORT_MINUTE:02d} tại múi giờ {VIETNAM_TZ} (hiện tại: {current_time})")
        job_queue.run_daily(
            callback=job_daily_report,
            time=time(hour=DAILY_REPORT_HOUR, minute=DAILY_REPORT_MINUTE, second=0, tzinfo=VIETNAM_TZ),
            chat_id=int(TELEGRAM_CHAT_ID)
        )
        
        # Lên lịch kiểm tra giá mỗi 30 phút
        logger.info("Lên lịch job kiểm tra giá mỗi 30 phút")
        job_queue.run_repeating(
            callback=job_check_price_change,
            interval=1800,
            first=10,
            chat_id=int(TELEGRAM_CHAT_ID)
        )
        
        logger.info("Bot đã sẵn sàng và các công việc đã được lên lịch!")
        application.run_polling()
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")

if __name__ == "__main__":
    main()