from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from bot.states import OrderFlow
from bot.config import ORDER_CHANNEL_ID
from shared.db import fetch_one, fetch_all, execute
from shared.settings import get_order_timeout, get_browser_message, is_membership_required
from bot.keyboards.main_menu import membership_button
import json
import asyncio

router = Router()

media_cache = {}


@router.message(F.text == "📦 Order")
async def start_order(msg: Message, state: FSMContext):
    user = await fetch_one("SELECT acc_no, membership_active FROM users WHERE tg_id = ?", [msg.from_user.id])
    if not user:
        await msg.answer("Pehle register karo /start")
        return
    acc_no, mem_active = user
    if await is_membership_required() and not mem_active:
        await msg.answer("❌ Order ke liye membership zaruri hai.\n\nPehle membership lo:", reply_markup=membership_button())
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
    amounts = await fetch_all(
        "SELECT id, amount, deposit_structure FROM deposit_amounts WHERE url_id = ? AND is_active = 1 AND used_count < max_limit ORDER BY amount",
        [next_id]
    )
    if not amounts:
        await msg.answer("❌ Is URL pe abhi koi deposit available nahi (sab limit cross).")
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
    await msg.answer(
        "📸 3 Photos ek saath bhejo (album):\n\n"
        "1️⃣ Deposit proof\n"
        "2️⃣ Withdrawal proof\n"
        "3️⃣ Game statistics proof\n\n"
        "Teeno select karke ek saath bhejo."
    )
    await state.set_state(OrderFlow.proof1)


@router.message(OrderFlow.proof1, F.photo)
async def order_proofs(msg: Message, state: FSMContext):
    if msg.media_group_id:
        gid = msg.media_group_id
        if gid not in media_cache:
            media_cache[gid] = {"file_ids": [], "user_id": msg.from_user.id}
        media_cache[gid]["file_ids"].append(msg.photo[-1].file_id)
        if len(media_cache[gid]["file_ids"]) == 1:
            async def process_album(gid=gid, msg=msg, state=state):
                await asyncio.sleep(3)
                if gid not in media_cache:
                    return
                cache = media_cache.pop(gid)
                file_ids = cache["file_ids"]
                await save_order_with_photos(msg, state, file_ids)
            asyncio.create_task(process_album())
    else:
        await save_order_with_photos(msg, state, [msg.photo[-1].file_id])


async def save_order_with_photos(msg: Message, state: FSMContext, file_ids: list):
    data = await state.get_data()
    timeout = await get_order_timeout()
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [msg.from_user.id])
    acc_no = user[0]
    
    # 1. ORDER SAVE KARO
    await execute(
        "INSERT INTO orders (user_acc, url_id, deposit_amount_id, deposit_amount, deposit_structure, working_url, uid, withdrawal_amount, proof_file_ids, proof_type, status, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'photo', 'created', DATETIME('now', '+' || ? || ' minutes'))",
        [acc_no, data["url_id"], data["deposit_id"], data["deposit_amount"], data["deposit_structure"], data["url"], data["uid"], data["withdrawal"], json.dumps(file_ids), timeout]
    )
    order = await fetch_one("SELECT last_insert_rowid()")
    order_id = order[0]
    
    # 2. CAPTION
    caption = (
        f"📦 Order #{order_id}\n"
        f"👤 User: {acc_no}\n"
        f"💰 Deposit: ₹{data['deposit_amount']:.0f}\n"
        f"📋 Structure: {data['deposit_structure']}\n"
        f"🔗 URL: {data['url']}\n"
        f"🔢 UID: {data['uid']}\n"
        f"💸 Withdrawal: ₹{data['withdrawal']:.0f}"
    )
    
    # 3. CHANNEL MEIN ALBUM BHEJO
    proof_msg_id = None
    try:
        if len(file_ids) >= 2:
            media = [InputMediaPhoto(media=fid, caption=caption if i == 0 else None) 
                     for i, fid in enumerate(file_ids)]
            sent = await msg.bot.send_media_group(ORDER_CHANNEL_ID, media)
            proof_msg_id = sent[0].message_id
        else:
            sent = await msg.bot.send_photo(ORDER_CHANNEL_ID, file_ids[0], caption=caption)
            proof_msg_id = sent.message_id
    except Exception as e:
        print(f"Channel send error: {e}")
    
    # 4. UPDATE ORDER
    if proof_msg_id:
        await execute("UPDATE orders SET proof_message_id = ?, proof_caption = ? WHERE id = ?",
                      [proof_msg_id, caption, order_id])
    
    # 5. STATUS = under_processing aur used_count +1
    await execute("UPDATE orders SET status = 'under_processing' WHERE id = ?", [order_id])
    await execute("UPDATE deposit_amounts SET used_count = used_count + 1 WHERE id = ?", [data["deposit_id"]])
    
    await state.clear()
    await msg.answer(f"✅ Order Submit Ho Gaya!\n\n📦 Order ID: #{order_id}\nPhotos: {len(file_ids)}\nStatus: Under Processing\n\nAdmin verify karega. {timeout} min tak wait karo.")
