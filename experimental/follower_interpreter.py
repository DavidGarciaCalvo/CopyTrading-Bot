def interpretar_senal_para_follower(signal, follower_position):
    signal_type = signal["signal_type"]

    if follower_position is None:
        if signal_type in {"OPEN_LONG", "INCREASE_LONG", "FLIP_SHORT_TO_LONG"}:
            return "OPEN_LONG"
        if signal_type in {"OPEN_SHORT", "INCREASE_SHORT", "FLIP_LONG_TO_SHORT"}:
            return "OPEN_SHORT"
        return "NO_ACTION"

    follower_side = follower_position["side"]

    if follower_side == "long":
        if signal_type in {"OPEN_LONG", "INCREASE_LONG"}:
            return "INCREASE_LONG"
        if signal_type == "REDUCE_LONG":
            return "REDUCE_LONG"
        if signal_type == "CLOSE_LONG":
            return "CLOSE_LONG"
        if signal_type in {"FLIP_LONG_TO_SHORT", "OPEN_SHORT", "INCREASE_SHORT"}:
            return "CLOSE_LONG_AND_OPEN_SHORT"
        if signal_type in {"REDUCE_SHORT", "CLOSE_SHORT", "FLIP_SHORT_TO_LONG"}:
            return "NO_ACTION"

    if follower_side == "short":
        if signal_type in {"OPEN_SHORT", "INCREASE_SHORT"}:
            return "INCREASE_SHORT"
        if signal_type == "REDUCE_SHORT":
            return "REDUCE_SHORT"
        if signal_type == "CLOSE_SHORT":
            return "CLOSE_SHORT"
        if signal_type in {"FLIP_SHORT_TO_LONG", "OPEN_LONG", "INCREASE_LONG"}:
            return "CLOSE_SHORT_AND_OPEN_LONG"
        if signal_type in {"REDUCE_LONG", "CLOSE_LONG", "FLIP_LONG_TO_SHORT"}:
            return "NO_ACTION"

    return "NO_ACTION"