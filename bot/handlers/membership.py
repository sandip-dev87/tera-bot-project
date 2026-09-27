from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import MembershipFlow
from shared.db import fetch_one, fetch_all, execute

router = Router()

@router.message(F.text == "/membership")
async def show_plans(msg: Message, state: FSMContext):
    plans = await fetch_all("SELECT id, name, price, duration_days FROM membership_plans WHERE is_active = 1")
    if not plans:
        await msg.answer("❌ Abhi koi plan available nahi.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p[1]} — ₹{p[2]:.0f} ({p[3]} din)", callback_data=f"plan_{p[0]}")]
        for p in plans
    ])
    await msg.answer("🎫 Membership Plans:\n\nChoose karo:", reply_markup=kb)

@router.callback_query(F.data.startswith("plan_"))
async def choose_plan(cb: CallbackQuery, state: FSMContext):
    plan_id = int(cb.data.split("_")[1])
    plan = await fetch_one("SELECT name, price, duration_days, qr_file_id FROM membership_plans WHERE id = ?", [plan_id])
    await state.update_data(plan_id=plan_id, plan_name=plan[0], amount=plan[1])
    text = f"🎫 {plan[0]}\nPrice: ₹{plan[1]:.0f}\nDuration: {plan[2]} din\n\nQR pe payment karo, phir UTR + screenshot bhejo."
    if plan[3]:
        await cb.message.answer_photo(plan[3], caption=text)
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
    await execute("INSERT INTO memberships (user_acc, plan_id, plan_name, amount, duration_days, utr, payment_proof_file_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')", [acc_no, data["plan_id"], data["plan_name"], data["amount"], 30, data["utr"], msg.photo[-1].file_id])
    await state.clear()
    await msg.answer("✅ Membership request submit! Admin approve karega.")
