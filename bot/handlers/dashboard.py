from aiogram import Router, F
from aiogram.types import Message
from shared.db import fetch_one

router = Router()

@router.message(F.text == "💰 Balance")
async def show_balance(msg: Message):
    user = await fetch_one("SELECT acc_no, balance, name FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo /start")
        return
    acc_no, balance, name = user
    await msg.answer(f"💰 Balance\n\n👤 {name}\n🎫 Acc No: {acc_no}\n💵 Balance: ₹{balance:,.0f}")

@router.message(F.text == "👤 Profile")
async def show_profile(msg: Message):
    user = await fetch_one("SELECT acc_no, name, mobile, balance, membership_active, membership_expiry FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo /start")
        return
    acc_no, name, mobile, balance, mem_active, mem_expiry = user
    mem_status = "❌ Nahi"
    if mem_active and mem_expiry:
        mem_status = f"✅ Active (expiry: {mem_expiry})"
    await msg.answer(f"👤 Profile\n\nNaam: {name}\nMobile: {mobile}\nAcc No: {acc_no}\nBalance: ₹{balance:,.0f}\nMembership: {mem_status}")
