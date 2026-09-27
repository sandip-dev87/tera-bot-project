from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import OrderFlow
from shared.db import fetch_one, fetch_all, execute
from shared.settings import get_order_timeout, get_browser_message, is_membership_required

router = Router()

@router.message(F.text == "📦 Order")
async def start_order(msg: Message, state: FSMContext):
    user = await fetch_one("SELECT acc_no, membership_active FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo /start")
        return
    acc_no, mem_active = user
    if await is_membership_required() and not mem_active:
        await msg.answer("❌ Order ke liye membership zaruri hai.\n\nMembership lo.")
        return
    urls = await fetch_all("SELECT id FROM working_urls WHERE is_active = 1 ORDER BY id")
    if not urls:
        await msg.answer("❌ Abhi koi URL available nahi hai.")
        return
    url_ids = [u[0] for u in urls]
    last = await fetch_one("SELECT last_url_id FROM url_rotation WHERE user_acc = ?", [acc_no])
    if not last or last[0] is None:
        next_id = url_ids[0]
    else:
        last_id = last[0]
        if last_id in url_ids:
            idx = url_ids.index(last_id)
            next_id = url_ids[(idx + 1) % len(url_ids)]
        else:
            next_id = url_ids[0]
    await execute("INSERT INTO url_rotation (user_acc, last_url_id) VALUES (?, ?) ON CONFLICT(user_acc) DO UPDATE SET last_url_id = ?", [acc_no, next_id, next_id])
    url_row = await fetch_one("SELECT url FROM working_urls WHERE id = ?", [next_id])
    url = url_row[0]
    amounts = await fetch_all("SELECT id, amount, deposit_structure FROM deposit_amounts WHERE url_id = ? AND is_active = 1 AND used_count < max_limit ORDER BY amount", [next_id])
    if not amounts:
        await msg.answer("❌ Is URL pe abhi koi deposit available nahi.")
        return
    await state.update_data(url_id=next_id, url=url)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"₹{a[1]:.0f} — {a[2]}", callback_data=f"dep_{a[0]}")]
        for a in amounts
    ])
    await msg.answer(f"📦 Order Create\n\n🔗 Working URL:\n<code>{url}</code>\n\nDeposit amount choose karo:", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("dep_"))
async def choose_deposit(cb: CallbackQuery, state: FSMContext):
    dep_id = int(cb.data.split("_")[1])
    dep = await fetch_one("SELECT amount, deposit_structure FROM deposit_amounts WHERE id = ?", [dep_id])
    data = await state.get_data()
    browser_msg = await get_browser_message()
    await state.update_data(deposit_id=dep_id, deposit_amount=dep[0], deposit_structure=dep[1])
    await cb.message.edit_text(f"✅ Deposit Selected: ₹{dep[0]:.0f}\n📋 Structure: {dep[1]}\n\n🔗 Working URL:\n<code>{data['url']}</code>\n\n📋 URL copy karne ke liye tap karo\n\n🌐 Ab {browser_msg}\nAur deposit karo.\n\nUID bhejo:", parse_mode="HTML")
    await state.set_state(OrderFlow.uid)

@router.message(OrderFlow.uid)
async def order_uid(msg: Message, state: FSMContext):
    await state.update_data(uid=msg.text.strip())
    await msg.answer("💸 Withdrawal amount bhejo:")
    await state.set_state(OrderFlow.withdrawal)

@router.message(OrderFlow.withdrawal)
async def order_withdrawal(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
    except:
        await msg.answer("❌ Number bhejo:")
        return
    await state.update_data(withdrawal=amt)
    await msg.answer("📸 Proof bhejo (photo):")
    await state.set_state(OrderFlow.proof)

@router.message(OrderFlow.proof, F.photo)
async def order_proof(msg: Message, state: FSMContext):
    data = await state.get_data()
    file_id = msg.photo[-1].file_id
    timeout = await get_order_timeout()
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [msg.from_user.id])
    acc_no = user[0]
    await execute("INSERT INTO orders (user_acc, url_id, deposit_amount_id, deposit_amount, deposit_structure, working_url, uid, withdrawal_amount, proof_file_ids, proof_type, status, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'photo', 'created', DATETIME('now', '+' || ? || ' minutes'))", [acc_no, data["url_id"], data["deposit_id"], data["deposit_amount"], data["deposit_structure"], data["url"], data["uid"], data["withdrawal"], file_id, timeout])
    order = await fetch_one("SELECT last_insert_rowid()")
    order_id = order[0]
    await state.clear()
    await msg.answer(f"✅ Order Submit Ho Gaya!\n\n📦 Order ID: #{order_id}\nStatus: Under Processing\n\nAdmin verify karega. {timeout} min tak wait karo.")
