from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states import Forgot
from shared.db import fetch_one, execute
from shared.utils import generate_otp, save_otp, verify_otp, hash_password

router = Router()

@router.message(F.text == "/forgot")
async def cmd_forgot(msg: Message, state: FSMContext):
    await msg.answer("🔐 Forgot Password\n\nMobile number bhejo:")
    await state.set_state(Forgot.mobile)

@router.message(Forgot.mobile)
async def forgot_mobile(msg: Message, state: FSMContext):
    mobile = msg.text.strip()
    user = await fetch_one("SELECT acc_no FROM users WHERE mobile = ?", [mobile])
    if not user:
        await msg.answer("❌ Ye mobile registered nahi hai.")
        await state.clear()
        return
    otp = generate_otp()
    await save_otp(mobile, otp)
    await state.update_data(mobile=mobile)
    await msg.answer(f"📱 Tumhara OTP: {otp}\n\n5 minute mein use karo.\n\nOTP bhejo:")
    await state.set_state(Forgot.otp)

@router.message(Forgot.otp)
async def forgot_otp(msg: Message, state: FSMContext):
    data = await state.get_data()
    result = await verify_otp(data["mobile"], msg.text.strip())
    if not result["ok"]:
        await msg.answer(f"❌ {result['msg']}")
        return
    await msg.answer("✅ OTP verified!\n\nNaya password bhejo:")
    await state.set_state(Forgot.new_password)

@router.message(Forgot.new_password)
async def forgot_new_password(msg: Message, state: FSMContext):
    data = await state.get_data()
    pwd = msg.text
    if len(pwd) < 4:
        await msg.answer("❌ Password 4+ characters:")
        return
    pwd_hash = hash_password(pwd)
    await execute("UPDATE users SET password_hash = ? WHERE mobile = ?", [pwd_hash, data["mobile"]])
    await state.clear()
    await msg.answer("✅ Password change ho gaya! Ab login karo.")
