from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from bot.states import MembershipFlow
from shared.db import fetch_one, fetch_all, execute

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
    
    # PAID PLAN - Normal flow
    await state.update_data(plan_id=plan_id, plan_name=plan_name, amount=price)
    text = f"🎫 {plan_name}\nPrice: ₹{price:.0f}\nDuration: {duration} din\n\nQR pe payment karo, phir UTR + screenshot bhejo."
    
    if qr_file_id:
        await cb.message.answer_photo(qr_file_id, caption=text)
    else:
        await cb.message.edit_text(text)
    
    await cb.message.answer("UTR bhejo:")
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
    await execute(
        "INSERT INTO memberships (user_acc, plan_id, plan_name, amount, duration_days, utr, payment_proof_file_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
        [acc_no, data["plan_id"], data["plan_name"], data["amount"], 30, data["utr"], msg.photo[-1].file_id]
    )
    await state.clear()
    await msg.answer("✅ Membership request submit! Admin approve karega.")
