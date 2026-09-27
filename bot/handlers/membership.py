from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import MembershipFlow
from shared.db import fetch_one, fetch_all, execute
from bot.config import MEMBERSHIP_CHANNEL_ID

router = Router()


async def show_membership_plans(target, state: FSMContext):
    plans = await fetch_all("SELECT id, name, price, duration_days, is_free FROM membership_plans WHERE is_active = 1")
    if not plans:
        await target.answer("❌ Abhi koi plan available nahi.")
        return
    buttons = []
    for p in plans:
        if p[4] == 1:
            label = f"🎁 {p[1]} — FREE ({p[3]} din)"
        else:
            label = f"{p[1]} — ₹{p[2]:.0f} ({p[3]} din)"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"plan_{p[0]}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await target.answer("🎫 Membership Plans:\n\nChoose karo:", reply_markup=kb)


@router.message(F.text == "/membership")
async def cmd_membership(msg: Message, state: FSMContext):
    await show_membership_plans(msg, state)


@router.message(F.text == "🎫 Membership")
async def menu_membership(msg: Message, state: FSMContext):
    await show_membership_plans(msg, state)


@router.callback_query(F.data == "show_plans")
async def cb_show_plans(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await show_membership_plans(cb.message, state)


@router.callback_query(F.data.startswith("plan_"))
async def choose_plan(cb: CallbackQuery, state: FSMContext):
    plan_id = int(cb.data.split("_")[1])
    plan = await fetch_one("SELECT name, price, duration_days, qr_file_id, is_free FROM membership_plans WHERE id = ?", [plan_id])
    plan_name, price, duration, qr_file_id, is_free = plan
    
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [cb.from_user.id])
    acc_no = user[0]
    
    # FREE PLAN - Auto approve
    if is_free == 1:
        from datetime import datetime, timedelta
        expiry = datetime.now() + timedelta(days=duration)
        await execute(
            "UPDATE users SET membership_active = 1, membership_expiry = ? WHERE acc_no = ?",
            [expiry, acc_no]
        )
        await execute(
            "INSERT INTO memberships (user_acc, plan_id, plan_name, amount, duration_days, status, approved_at) VALUES (?, ?, ?, 0, ?, 'approved', CURRENT_TIMESTAMP)",
            [acc_no, plan_id, plan_name, duration]
        )
        await cb.message.edit_text(
            f"🎁 Free Membership Active!\n\n"
            f"Plan: {plan_name}\n"
            f"Duration: {duration} din\n"
            f"Expiry: {expiry.strftime('%Y-%m-%d')}\n\n"
            f"✅ Ab tum order kar sakte ho."
        )
        await state.clear()
        return
    
    # PAID PLAN - QR dikhao
    await state.update_data(plan_id=plan_id, plan_name=plan_name, amount=price, duration=duration)
    
    text = (
        f"🎫 {plan_name}\n"
        f"💰 Price: ₹{price:.0f}\n"
        f"📅 Duration: {duration} din\n\n"
        f"QR scan karke payment karo.\n"
        f"Payment ke baad UTR + screenshot bhejo."
    )
    
    if qr_file_id:
        await cb.message.answer_photo(qr_file_id, caption=text)
    else:
        await cb.message.edit_text(text + "\n\n⚠️ QR available nahi hai. Admin se contact karo.")
        return
    
    await cb.message.answer("📝 UTR (Transaction ID) bhejo:")
    await state.set_state(MembershipFlow.utr)


@router.message(MembershipFlow.utr)
async def membership_utr(msg: Message, state: FSMContext):
    await state.update_data(utr=msg.text.strip())
    await msg.answer("📸 Payment screenshot bhejo:")
    await state.set_state(MembershipFlow.proof)


@router.message(MembershipFlow.proof, F.photo)
async def membership_proof(msg: Message, state: FSMContext):
    data = await state.get_data()
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [msg.from_user.id])
    acc_no = user[0]
    
    # Channel mein bhejo
    caption = (
        f"🎫 Membership Request\n"
        f"👤 User: {acc_no}\n"
        f"📦 Plan: {data['plan_name']}\n"
        f"💰 Amount: ₹{data['amount']:.0f}\n"
        f"📝 UTR: {data['utr']}"
    )
    
    proof_msg_id = None
    try:
        sent = await msg.bot.send_photo(
            MEMBERSHIP_CHANNEL_ID,
            msg.photo[-1].file_id,
            caption=caption
        )
        proof_msg_id = sent.message_id
    except Exception as e:
        print(f"Membership channel error: {e}")
    
    await execute(
        "INSERT INTO memberships (user_acc, plan_id, plan_name, amount, duration_days, utr, payment_proof_file_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
        [acc_no, data["plan_id"], data["plan_name"], data["amount"], data["duration"], data["utr"], msg.photo[-1].file_id]
    )
    
    await state.clear()
    await msg.answer("✅ Membership request submit! Admin approve karega.")


# ===== ADMIN COMMAND: QR SET KAR =====

@router.message(F.text == "/setqr")
async def cmd_setqr(msg: Message, state: FSMContext):
    plans = await fetch_all("SELECT id, name, price FROM membership_plans WHERE is_active = 1 AND is_free = 0")
    if not plans:
        await msg.answer("❌ Koi paid plan nahi hai.")
        return
    buttons = [[InlineKeyboardButton(text=f"{p[1]} — ₹{p[2]:.0f}", callback_data=f"setqr_{p[0]}")] for p in plans]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await msg.answer("📸 Kis plan ka QR set karna hai?", reply_markup=kb)


@router.callback_query(F.data.startswith("setqr_"))
async def cb_setqr(cb: CallbackQuery, state: FSMContext):
    plan_id = int(cb.data.split("_")[1])
    await state.update_data(setqr_plan_id=plan_id)
    await cb.message.edit_text("📸 Ab QR image bhejo:")
    await state.set_state("waiting_qr")


@router.message(F.photo, lambda m: True)
async def handle_qr_photo(msg: Message, state: FSMContext):
    # Check karo QR set kar rahe hain?
    data = await state.get_data()
    plan_id = data.get("setqr_plan_id")
    
    if not plan_id:
        return  # Normal photo hai, ignore
    
    # QR Telegram mein save karo
    qr_msg_id = None
    try:
        sent = await msg.bot.send_photo(
            MEMBERSHIP_CHANNEL_ID,
            msg.photo[-1].file_id,
            caption=f"QR for Plan #{plan_id}"
        )
        qr_msg_id = sent.message_id
    except Exception as e:
        print(f"QR save error: {e}")
    
    # Turso mein qr_file_id save
    file_id = msg.photo[-1].file_id
    await execute("UPDATE membership_plans SET qr_file_id = ? WHERE id = ?", [file_id, plan_id])
    
    await state.clear()
    await msg.answer(f"✅ QR set ho gaya plan #{plan_id} ke liye!")
