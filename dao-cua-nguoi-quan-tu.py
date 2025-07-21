import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import json
import os
import random
import logging
import pytz
from datetime import time
import asyncio

# --- CẤU HÌNH ---
# Token và tên file JSON đã được cập nhật
BOT_TOKEN = "7198310816:AAGhM-YSpecOD37NgXHwrshdjIx-paJJwoA"
JSON_FILE = "dao-cua-nguoi-quan-tu.json"

CHAT_ID_DAILY = "5882369573" # ID kênh/nhóm để gửi quẻ hàng ngày
STATE_FILE = "current_que_index.txt"
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
MESSAGE_CHAR_LIMIT = 4096 # Giới hạn ký tự của Telegram

# --- Thiết lập logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Tải dữ liệu Kinh Dịch ---
try:
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        ALL_QUES = json.load(f)
except FileNotFoundError:
    logger.error(f"LỖI: Không tìm thấy file '{JSON_FILE}'.")
    ALL_QUES = []
except json.JSONDecodeError:
    logger.error(f"LỖI: File '{JSON_FILE}' không phải là file JSON hợp lệ.")
    ALL_QUES = []

#=================================================================#
# CÁC HÀM HỖ TRỢ
#=================================================================#

def get_current_index():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try: return int(f.read().strip())
            except: return 0
    return 0

def save_current_index(index):
    with open(STATE_FILE, 'w') as f: f.write(str(index))

async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """Tự động chia nhỏ và gửi tin nhắn nếu nó quá dài."""
    if len(text) <= MESSAGE_CHAR_LIMIT:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    else:
        logger.info(f"Tin nhắn quá dài ({len(text)} chars). Đang tiến hành chia nhỏ...")
        for i in range(0, len(text), MESSAGE_CHAR_LIMIT):
            chunk = text[i:i + MESSAGE_CHAR_LIMIT]
            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
            await asyncio.sleep(0.5)

# *** CẬP NHẬT để dùng đúng key 'hao_tu' ***
async def send_que_details(context: ContextTypes.DEFAULT_TYPE, chat_id: int, que_data: dict):
    """Hàm chung để gửi chi tiết một quẻ (chính và các hào)."""
    try:
        main_message = format_que_message(que_data)
        await send_long_message(context, chat_id, main_message)
        await asyncio.sleep(1)

        # Cập nhật từ 'cac_hao' thành 'hao_tu'
        for hao in que_data.get('hao_tu', []):
            hao_message = format_hao_message(hao)
            await send_long_message(context, chat_id, hao_message)
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Lỗi khi gửi chi tiết quẻ: {e}", exc_info=True)


#=================================================================#
# CÁC HÀM ĐỊNH DẠNG TIN NHẮN (ĐÃ SỬA)
#=================================================================#

# *** CẬP NHẬT để đọc đúng cấu trúc file JSON mới ***
def format_que_message(que_data):
    message = f"🔮 <b>Quẻ số {que_data['so_que']}: {que_data['ten_que']} ({que_data['ten_tieng_trung']})</b> 🔮\n\n"
    hinh_que_info = que_data.get('hinh_que', {})
    message += f"<b>Hình quẻ:</b> {hinh_que_info.get('mo_ta', 'N/A')} (Ngoại: {hinh_que_info.get('ngoai_quai', '?')} | Nội: {hinh_que_info.get('noi_quai', '?')})\n\n"
    
    thoan_tu_info = que_data.get('thoan_tu', {})
    message += f"📖 <b>Thoán từ:</b>\n"
    message += f"<i><b>- Dịch âm:</b> {thoan_tu_info.get('dich_am', 'N/A')}</i>\n"
    message += f"<i><b>- Dịch nghĩa:</b> {thoan_tu_info.get('dich_nghia', 'N/A')}</i>\n\n"
    
    message += "📜 <b>Giải nghĩa Thoán từ:</b>\n"
    message += f"{que_data.get('giai_nghia_thoan_tu', 'Không có giải nghĩa.')}\n"
    return message

# *** CẬP NHẬT để đọc đúng cấu trúc file JSON mới ***
def format_hao_message(hao_data):
    message = f"爻 <b>{hao_data['ten_hao']}</b> 爻\n\n"
    message += f"📖 <b>Hào từ:</b>\n"
    message += f"<i><b>- Dịch âm:</b> {hao_data.get('dich_am', 'N/A')}</i>\n"
    message += f"<i><b>- Dịch nghĩa:</b> {hao_data.get('dich_nghia', 'N/A')}</i>\n\n"
    message += "📜 <b>Giải nghĩa:</b>\n"
    message += f"{hao_data.get('giai_nghia', 'Không có giải nghĩa.')}\n"
    return message

#=================================================================#
# CÁC HÀM XỬ LÝ LỆNH & MENU
#=================================================================#

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = (
        f"Xin chào {user.first_name}!\n\n"
        "Tôi là Bot Kinh Dịch. Tôi có thể giúp bạn:\n"
        "1. Tự động gửi một quẻ mỗi ngày vào kênh.\n"
        "2. Gieo một quẻ ngẫu nhiên cho bạn.\n"
        "3. Tra cứu thông tin chi tiết 64 quẻ.\n\n"
        "<b>Các lệnh có sẵn:</b>\n"
        "/random - 🎲 Gieo một quẻ ngẫu nhiên\n"
        "/chonque - 📜 Mở menu chọn quẻ\n"
    )
    await update.message.reply_html(message)

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ALL_QUES: return
    logger.info(f"{update.effective_user.username} gieo quẻ ngẫu nhiên.")
    random_que = random.choice(ALL_QUES)
    await update.message.reply_text(f"🎲 Quẻ ngẫu nhiên của bạn là: <b>{random_que['ten_que']}</b>", parse_mode='HTML')
    await send_que_details(context, update.effective_chat.id, random_que)

# *** CẬP NHẬT để dùng đúng key 'so_que' ***
def create_que_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    if not ALL_QUES: return None
    
    keyboard = []
    items_per_page = 10
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    
    page_ques = ALL_QUES[start_index:end_index]
    for i in range(0, len(page_ques), 2):
        # Dùng 'so_que' thay cho 'id'
        que1 = page_ques[i]
        row = [InlineKeyboardButton(f"{que1['so_que']}. {que1['ten_que']}", callback_data=f"que_select_{que1['so_que']}")]
        if i + 1 < len(page_ques):
            que2 = page_ques[i+1]
            row.append(InlineKeyboardButton(f"{que2['so_que']}. {que2['ten_que']}", callback_data=f"que_select_{que2['so_que']}"))
        keyboard.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Trước", callback_data=f"page_{page-1}"))
    if end_index < len(ALL_QUES):
        nav_buttons.append(InlineKeyboardButton("Sau ▶️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    return InlineKeyboardMarkup(keyboard)

async def select_que_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"{update.effective_user.username} mở menu chọn quẻ.")
    keyboard = create_que_keyboard(page=0)
    if keyboard:
        await update.message.reply_text("📜 Vui lòng chọn một quẻ từ danh sách:", reply_markup=keyboard)

# *** CẬP NHẬT để dùng đúng key 'so_que' ***
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("page_"):
        page = int(callback_data.split('_')[1])
        keyboard = create_que_keyboard(page)
        await query.edit_message_text(text=f"📜 Vui lòng chọn một quẻ từ danh sách (Trang {page+1}):", reply_markup=keyboard)
    
    elif callback_data.startswith("que_select_"):
        que_id = int(callback_data.split('_')[2])
        # Dùng 'so_que' thay cho 'id'
        selected_que = next((que for que in ALL_QUES if que['so_que'] == que_id), None)
        
        if selected_que:
            await query.edit_message_text(text=f"Bạn đã chọn: 🔮 <b>{selected_que['ten_que']}</b>", parse_mode='HTML')
            await send_que_details(context, query.message.chat_id, selected_que)

#=================================================================#
# CÔNG VIỆC HÀNG NGÀY (Daily Job)
#=================================================================#

async def job_send_daily_que(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Công việc được lập lịch để gửi quẻ mỗi ngày."""
    if not ALL_QUES: return
    
    current_index = get_current_index()
    if current_index >= len(ALL_QUES): current_index = 0
    que_to_send = ALL_QUES[current_index]
    
    logger.info(f"(DAILY JOB) Gửi quẻ số {que_to_send['so_que']}: {que_to_send['ten_que']}...")
    await send_que_details(context, CHAT_ID_DAILY, que_to_send)
    
    next_index = (current_index + 1) % len(ALL_QUES)
    save_current_index(next_index)
    logger.info("(DAILY JOB) Đã gửi thành công!")

#=================================================================#
# HÀM MAIN
#=================================================================#

def main() -> None:
    """Hàm chính để khởi tạo và chạy bot."""
    if not BOT_TOKEN:
        logger.critical("LỖI: BOT_TOKEN chưa được cung cấp.")
        return
    if not ALL_QUES:
        logger.critical("Bot không thể chạy vì không có dữ liệu quẻ.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("chonque", select_que_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    job_queue = application.job_queue
    # Lập lịch gửi quẻ hàng ngày vào 8:00 sáng, giờ Việt Nam
    job_queue.run_daily(job_send_daily_que, time=time(hour=8, minute=0, tzinfo=VIETNAM_TZ), name="daily_que_job")
    
    logger.info("Bot đã sẵn sàng và đang lắng nghe...")
    
    application.run_polling()

if __name__ == "__main__":
    main()