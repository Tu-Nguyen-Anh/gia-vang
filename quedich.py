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
BOT_TOKEN = "7913917084:AAHihvPMk4AuxoUsX37xmQjT0L4LXsBK3g4"
CHAT_ID_DAILY = "5882369573" # ID kênh/nhóm để gửi quẻ hàng ngày
JSON_FILE = "quedich.json"
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

# *** HÀM MỚI ĐỂ XỬ LÝ TIN NHẮN DÀI ***
async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """Tự động chia nhỏ và gửi tin nhắn nếu nó quá dài."""
    if len(text) <= MESSAGE_CHAR_LIMIT:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    else:
        logger.info(f"Tin nhắn quá dài ({len(text)} chars). Đang tiến hành chia nhỏ...")
        for i in range(0, len(text), MESSAGE_CHAR_LIMIT):
            chunk = text[i:i + MESSAGE_CHAR_LIMIT]
            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
            await asyncio.sleep(0.5) # Thêm một khoảng nghỉ nhỏ giữa các tin nhắn

# *** HÀM send_que_details ĐƯỢC CẬP NHẬT ĐỂ SỬ DỤNG HÀM MỚI ***
async def send_que_details(context: ContextTypes.DEFAULT_TYPE, chat_id: int, que_data: dict):
    """Hàm chung để gửi chi tiết một quẻ (chính và các hào)."""
    try:
        # Gửi thông tin chính của quẻ
        main_message = format_que_message(que_data)
        await send_long_message(context, chat_id, main_message)
        await asyncio.sleep(1)

        # Gửi lần lượt thông tin của từng hào
        for hao in que_data.get('cac_hao', []):
            hao_message = format_hao_message(hao)
            await send_long_message(context, chat_id, hao_message)
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Lỗi khi gửi chi tiết quẻ: {e}", exc_info=True)


#=================================================================#
# CÁC HÀM ĐỊNH DẠNG TIN NHẮN (Không thay đổi)
#=================================================================#

def format_que_message(que_data):
    message = f"🔮 <b>Quẻ số {que_data['id']}: {que_data['ten_que']}</b> 🔮\n\n"
    message += f"<b>Hình quẻ:</b> {que_data['hinh_que']}\n\n"
    message += f"📖 <b>Kinh văn:</b>\n"
    message += f"<i><b>- Dịch âm:</b> {que_data['kinh_van']['dich_am']}</i>\n"
    message += f"<i><b>- Dịch nghĩa:</b> {que_data['kinh_van']['dich_nghia']}</i>\n\n"
    message += "📜 <b>Giải nghĩa Kinh văn:</b>\n"
    for giai_nghia in que_data.get('giai_nghia_kinh_van', []):
        message += f"  - <b>{giai_nghia['tac_gia']}:</b> {giai_nghia['noi_dung']}\n"
    return message

def format_hao_message(hao_data):
    message = f"爻 <b>{hao_data['ten_hao']}</b> 爻\n\n"
    message += f"📖 <b>Kinh văn:</b>\n"
    message += f"<i><b>- Dịch âm:</b> {hao_data['kinh_van']['dich_am']}</i>\n"
    message += f"<i><b>- Dịch nghĩa:</b> {hao_data['kinh_van']['dich_nghia']}</i>\n\n"
    message += "📜 <b>Giải nghĩa:</b>\n"
    for giai_nghia in hao_data.get('giai_nghia', []):
        message += f"  - <b>{giai_nghia['tac_gia']}:</b> {giai_nghia['noi_dung']}\n"
    return message

#=================================================================#
# CÁC HÀM XỬ LÝ LỆNH & MENU (Không thay đổi)
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

def create_que_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    if not ALL_QUES: return None
    
    keyboard = []
    items_per_page = 10
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    
    page_ques = ALL_QUES[start_index:end_index]
    for i in range(0, len(page_ques), 2):
        row = [InlineKeyboardButton(f"{page_ques[i]['id']}. {page_ques[i]['ten_que']}", callback_data=f"que_select_{page_ques[i]['id']}")]
        if i + 1 < len(page_ques):
            row.append(InlineKeyboardButton(f"{page_ques[i+1]['id']}. {page_ques[i+1]['ten_que']}", callback_data=f"que_select_{page_ques[i+1]['id']}"))
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
        selected_que = next((que for que in ALL_QUES if que['id'] == que_id), None)
        
        if selected_que:
            await query.edit_message_text(text=f"Bạn đã chọn: 🔮 <b>{selected_que['ten_que']}</b>", parse_mode='HTML')
            await send_que_details(context, query.message.chat_id, selected_que)

#=================================================================#
# CÔNG VIỆC HÀNG NGÀY (Daily Job) - Không thay đổi
#=================================================================#

async def job_send_daily_que(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Công việc được lập lịch để gửi quẻ mỗi ngày."""
    if not ALL_QUES: return
    
    current_index = get_current_index()
    if current_index >= len(ALL_QUES): current_index = 0
    que_to_send = ALL_QUES[current_index]
    
    logger.info(f"(DAILY JOB) Gửi quẻ số {que_to_send['id']}: {que_to_send['ten_que']}...")
    await send_que_details(context, CHAT_ID_DAILY, que_to_send)
    
    next_index = (current_index + 1) % len(ALL_QUES)
    save_current_index(next_index)
    logger.info("(DAILY JOB) Đã gửi thành công!")

#=================================================================#
# HÀM MAIN (Không thay đổi)
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
    job_queue.run_daily(job_send_daily_que, time=time(hour=8, minute=0, tzinfo=VIETNAM_TZ), name="daily_que_job")
    
    logger.info("Bot đã sẵn sàng và đang lắng nghe...")
    
    application.run_polling()

if __name__ == "__main__":
    main()