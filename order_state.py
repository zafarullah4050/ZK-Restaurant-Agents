# order_state.py
# Keeps track of current order/reservation per user (in-memory)
# NOTE: This is in-memory. For production, use a proper database.

order_state = {}
reservation_state = {}
