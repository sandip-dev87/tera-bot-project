from aiogram.fsm.state import State, StatesGroup

class Register(StatesGroup):
    name = State()
    mobile = State()
    password = State()
    referral = State()

class Login(StatesGroup):
    mobile = State()
    password = State()

class Forgot(StatesGroup):
    mobile = State()
    otp = State()
    new_password = State()

class OrderFlow(StatesGroup):
    choose_amount = State()
    uid = State()
    withdrawal = State()
    proof = State()

class WithdrawFlow(StatesGroup):
    method = State()
    amount = State()
    details = State()

class MembershipFlow(StatesGroup):
    utr = State()
    proof = State()
