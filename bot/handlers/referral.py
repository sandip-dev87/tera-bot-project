from aiogram import Router, F
from aiogram.types import Message
from shared.db import fetch_one, fetch_all

router = Router()

@router.message(F.text == "👥 Referral")
async def show_referral(msg: Message):
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo")
        return
    acc_no = user[0]
    count = await fetch_one("SELECT COUNT(*) FROM referrals WHERE referrer_acc = ?", [acc_no])
    earned = await fetch_one("SELECT COALESCE(SUM(commission_earned), 0) FROM referrals WHERE referrer_acc = ?", [acc_no])
    refs = await fetch_all("SELECT r.referred_acc, r.commission_earned, u.name FROM referrals r JOIN users u ON u.acc_no = r.referred_acc WHERE r.referrer_acc = ?", [acc_no])
    text = f"👥 Referral\n\nTumhara Acc No: {acc_no}\nTotal Referrals: {count[0]}\nTotal Earned: ₹{earned[0]:,.0f}\n\n"
    if refs:
        text += "Referral List:\n"
        for ref in refs:
            text += f"• {ref[0]} ({ref[2]}) — ₹{ref[1]:.0f}\n"
    await msg.answer(text)
