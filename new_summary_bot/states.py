from aiogram.fsm.state import State, StatesGroup

class StartDialog(StatesGroup):
    waiting_for_show_example = State()
    waiting_for_channel_forward = State()
    waiting_for_schedule_time = State()
    waiting_for_user_local_time = State()

class AddChannelsState(StatesGroup):
    waiting_for_new_channels = State()

class DeleteChannelsState(StatesGroup):
    waiting_for_delete_choice = State()

class AddTopicsState(StatesGroup):
    waiting_for_topics_input = State()
    waiting_for_confirmation = State()

class EditTopicsState(StatesGroup):
    waiting_for_delete_topic = State()

class PaymentEmailState(StatesGroup):
    waiting_for_email = State()

class ChatState(StatesGroup):
    waiting_for_user_message = State()

class SummaryRetryStates(StatesGroup):
    waiting_for_retry_choice = State()
