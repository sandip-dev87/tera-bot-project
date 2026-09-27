from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import Register
from bot.keyboards.main_menu import main_menu, start_menu
from shared.db import fetch_one, execute
from shared.utils import generate_acc_no, hash_password, is_valid_mobile, is_valid_password

router = Router()

@router.message(F.text == "/start")
async def cmd_start(msg: Message):
    user = await fetch_one("SELECT acc_no FROM users WHERE tg_id = ?", [msg.from_user.id])
    if user:
        await msg.answer(f"Welcome back! 👋\nAcc No: {user[0]}", reply_markup=main_menu())
    else:
        await msg.answer("Welcome! 👋\n\nPehle register karo ya login karo:", reply_markup=start_menu())

@router.callback_query(F.data == "register")
async def cb_register(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("📝 Registration\n\nApna naam bhejo:")
    await state.set_state(Register.name)

@router.message(Register.name)
async def reg_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Mobile number bhejo (10 digit):")
    await state.set_state(Register.mobile)

@router.message(Register.mobile)
async def reg_mobile(msg: Message, state: FSMContext):
    mobile = msg.text.strip()
    if not is_valid_mobile(mobile):
        await msg.answer("❌ Sahi 10 digit mobile bhejo:")
        return
    existing = await fetch_one("SELECT acc_no FROM users WHERE mobile = ?", [mobile])
    if existing:
        await msg.answer("❌ Ye mobile already registered hai. Login karo.")
        return
    await state.update_data(mobile=mobile)
    await msg.answer("Password banao (4+ characters):")
    await state.set_state(Register.password)

@router.message(Register.password)
async def reg_password(msg: Message, state: FSMContext):
    pwd = msg.text
    if not is_valid_password(pwd):
        await msg.answer("❌ Password 4+ characters ka hona chahiye:")
        return
    await state.update_data(password=pwd)
    await msg.answer("Referral Acc No bhejo (agar hai):\n\nYa 'skip' likho:")
    await state.set_state(Register.referral)

@router.message(Register.referral)
async def reg_referral(msg: Message, state: FSMContext):
    ref = msg.text.strip()
    data = await state.get_data()
    referred_by = None
    if ref.lower() != "skip":
        ref_user = await fetch_one("SELECT acc_no FROM users WHERE acc_no = ?", [ref])
        if not ref_user:
            await msg.answer("❌ Referral Acc No galat hai. 'skip' likho ya sahi daalo:")
            return
        referred_by = ref
    acc_no = await generate_acc_no()
    pwd_hash = hash_password(data["password"])
    await execute(
        "INSERT INTO users (acc_no, tg_id, name, mobile, password_hash, referred_by) VALUES (?, ?, ?, ?, ?, ?)",
        [acc_no, msg.from_user.id, data["name"], data["mobile"], pwd_hash, referred_by]
    )
    if referred_by:
        await execute("INSERT INTO referrals (referrer_acc, referred_acc) VALUES (?, ?)", [referred_by, acc_no])
    await state.clear()
    await msg.answer(
        f"✅ Registration Complete!\n\n👤 Naam: {data['name']}\n📱 Mobile: {data['mobile']}\n🎫 Acc No: {acc_no}\n\nYe Acc No yaad rakhna (referral ke liye).",
        reply_markup=main_menu()
    )
