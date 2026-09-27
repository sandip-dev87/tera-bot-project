from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import WithdrawFlow
from shared.db import fetch_one, execute
from shared.settings import get_crypto_fee, get_upi_fee, get_bank_fee

router = Router()

@router.message(F.text == "💸 Withdraw")
async def start_withdraw(msg: Message, state: FSMContext):
    user = await fetch_one("SELECT acc_no, balance FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo")
        return
    await state.update_data(acc_no=user[0], balance=user[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Crypto", callback_data="wd_crypto")],
        [InlineKeyboardButton(text="📱 UPI", callback_data="wd_upi")],
        [InlineKeyboardButton(text="🏦 Bank", callback_data="wd_bank")],
    ])
    await msg.answer(f"💸 Withdrawal\n\nBalance: ₹{user[1]:,.0f}\n\nMethod choose karo:", reply_markup=kb)

@router.callback_query(F.data.startswith("wd_"))
async def choose_method(cb: CallbackQuery, state: FSMContext):
    method = cb.data.split("_")[1]
    fees = {"crypto": await get_crypto_fee(), "upi": await get_upi_fee(), "bank": await get_bank_fee()}
    await state.update_data(method=method, fee=fees[method])
    await cb.message.edit_text(f"Method: {method.upper()}\nProcessing Fee: ₹{fees[method]:.0f}\n\nKitna withdraw karna hai? (number bhejo)")
    await state.set_state(WithdrawFlow.amount)

@router.message(WithdrawFlow.amount)
async def withdraw_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.strip())
    except:
        await msg.answer("❌ Number bhejo:")
        return
    data = await state.get_data()
    total = amount + data["fee"]
    if data["balance"] < total:
        await msg.answer(f"❌ Insufficient balance!\n\nChahiye: ₹{total:.0f}\nHai: ₹{data['balance']:.0f}")
        return
    await state.update_data(amount=amount, total=total)
    method = data["method"]
    if method == "crypto":
        await msg.answer("🪙 Wallet address bhejo:")
    elif method == "upi":
        await msg.answer("📱 UPI ID bhejo:")
    else:
        await msg.answer("🏦 Account number bhejo:")
    await state.set_state(WithdrawFlow.details)

@router.message(WithdrawFlow.details)
async def withdraw_details(msg: Message, state: FSMContext):
    data = await state.get_data()
    details = msg.text.strip()
    await state.update_data(details=details)
    method = data["method"]
    if method == "upi" and "holder_done" not in data:
        await state.update_data(holder_done=True)
        await msg.answer("📱 Account holder name bhejo:")
        return
    await execute("INSERT INTO withdrawals (user_acc, amount, processing_fee, total_deducted, method, wallet_address, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')", [data["acc_no"], data["amount"], data["fee"], data["total"], method, details])
    await execute("UPDATE users SET balance = balance - ? WHERE acc_no = ?", [data["total"], data["acc_no"]])
    await state.clear()
    await msg.answer(f"✅ Withdrawal Request Submit!\n\nAmount: ₹{data['amount']:.0f}\nFee: ₹{data['fee']:.0f}\nTotal Deduct: ₹{data['total']:.0f}\n\nAdmin approve karega.")
