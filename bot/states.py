from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_tags = State()
    waiting_for_time = State()
    waiting_for_time_start = State()
    waiting_for_channel_start = State()
    waiting_for_first_action = State()
    waiting_for_delete = State()
