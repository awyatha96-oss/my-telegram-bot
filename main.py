import os
import asyncio
import io
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import google.generativeai as genai

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "@reeac_99"

# Gemini Setup
genai.configure(api_key=GEMINI_KEY)

# Flask Server for Render
app = Flask('')
@app.route('/')
def home(): return "Gemini TTS Bot is Online"
def run(): app.run(host='0.0.0.0', port=10000)

JOIN_CHECK, GET_TEXT, SELECT_VOICE = range(3)

# အသံကို Nilar (Female) နှင့် Thiha (Male) အဖြစ် ပြောင်းလဲသတ်မှတ်ခြင်း
GEMINI_VOICES = {
    "Nilar (Female) 👩": "aoede",
    "Thiha (Male) 👨": "charon"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['left', 'kicked']:
            keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
                        [InlineKeyboardButton("I have joined ✅", callback_data="check_join")]]
            await update.message.reply_text("ရှေ့ဆက်ဖို့ Channel အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
            return JOIN_CHECK
        await update.message.reply_text("Gemini Smart Voice Bot မှ ကြိုဆိုပါတယ်။\nအသံပြောင်းလိုသော စာသားကို ရိုက်ထည့်ပေးပါ။")
        return GET_TEXT
    except:
        await update.message.reply_text("Error: Bot ကို Channel မှာ Admin ခန့်ထားပါသလား ပြန်စစ်ပေးပါ။")
        return ConversationHandler.END

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=query.from_user.id)
    if member.status not in ['left', 'kicked']:
        await query.message.delete()
        await context.bot.send_message(chat_id=query.from_user.id, text="စာသားကို ရိုက်ထည့်နိုင်ပါပြီ။")
        return GET_TEXT
    return JOIN_CHECK

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['text_to_convert'] = update.message.text
    keyboard = [[InlineKeyboardButton(name, callback_data=name) for name in GEMINI_VOICES.keys()]]
    await update.message.reply_text("အသုံးပြုလိုသော အသံကို ရွေးချယ်ပါ -", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_VOICE

async def handle_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    voice_display_name = query.data
    voice_id = GEMINI_VOICES[voice_display_name]
    text = context.user_data.get('text_to_convert')
    await query.answer()
    
    msg = await query.edit_message_text(f"⏳ {voice_display_name} ဖြင့် အသံဖန်တီးနေပါသည်...")

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            contents=text,
            generation_config={
                "response_mime_type": "audio/mp3",
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_id": voice_id
                    }
                }
            }
        )

        if hasattr(response, 'audio_contents') and response.audio_contents:
            audio_data = response.audio_contents[0].data
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"{voice_display_name}.mp3"
            await query.message.reply_audio(audio=audio_file, caption=f"🎙 Voice: {voice_display_name}")
            await msg.delete()
        else:
            await query.edit_message_text("Error: Gemini API မှ အသံဒေတာ မရရှိပါ။ (Key သို့မဟုတ် Region ကန့်သတ်ချက် ဖြစ်နိုင်သည်)")
    except Exception as e:
        await query.edit_message_text(f"Error: {str(e)}")
    
    return GET_TEXT

def main():
    Thread(target=run).start()
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            JOIN_CHECK: [CallbackQueryHandler(check_join_callback, pattern="^check_join$")],
            GET_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            SELECT_VOICE: [CallbackQueryHandler(handle_voice_selection)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    application.add_handler(conv_handler)
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
