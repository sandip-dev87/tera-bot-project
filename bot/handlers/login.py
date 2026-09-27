from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import Login
from bot.keyboards.main_menu import main_menu
from shared.db import fetch_one
from shared.utils import verify_password

router = Router()

@router.callback_query(F.data == "login")
async def cb_login(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("🔐 Login\n\nMobile number bhejo:")
    await state.set_state(Login.mobile)

@router.message(Login.mobile)
async def login_mobile(msg: Message, state: FSMContext):
    await state.update_data(mobile=msg.text.strip())
    await msg.answer("Password bhejo:")
    await state.set_state(Login.password)

@router.message(Login.password)
async def login_password(msg: Message, state: FSMContext):
    data = await state.get_data()
    user = await fetch_one("SELECT acc_no, password_hash, is_banned FROM users WHERE mobile = ?", [data["mobile"]])
    if not user:
        await msg.answer("❌ User nahi mila. Register karo.")
        await state.clear()
        return
    acc_no, pwd_hash, is_banned = user
    if is_banned:
        await msg.answer("❌ Tumhara account ban hai.")
        await state.clear()
        return
    if not verify_password(msg.text, pwd_hash):
        await msg.answer("❌ Galat password")
        await state.clear()
        return
    await state.clear()
    await msg.answer(f"✅ Login successful!\n\nAcc No: {acc_no}", reply_markup=main_menu())
