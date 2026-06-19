from enum import StrEnum

__all__ = (
    "Event",
    "Reason",
)


class Event(StrEnum):
    # Dispatched after a queue is filled to maximum occupancy
    QUEUE_FILLED = "queue_filled"

    # Dispatched after queue owner submits prematch modal successfully
    PREMATCH_MODAL_DONE = "prematch_modal_done"

    # Dispatched after the prematch DM is ready to be sent
    PREMATCH_DM_READY_SEND = "prematch_dm_ready_send"

    # Dispatched after cancel button was pressed to delete prematch DM message
    PREMATCH_DM_DELETE = "prematch_dm_delete"

    # Dispatched after the reset button was pressed
    RESET_BUTTON_PRESSED = "reset_button_pressed"
    
    # Dispatched after the cancel button was pressed to destroy temporary voice channels
    CANCEL_BUTTON_PRESSED = "cancel_button_pressed"

    # Dispatched after match has been finalised (win + mvp set for both teams)
    MATCH_FINALISED = "match_finalised"

    # Dispatched after match finalised to lock and close the thread
    THREAD_CLEANUP = "postmatch_thread_cleanup"

    # Dispatched after a season has been stopped and rankings are finalised
    SEASON_STOP = "season_stop"

    # Dispatched after a player's stats have been reset
    PLAYER_STATS_RESET = "player_stats_reset"

    # Dispatched after a player's stats have been deleted
    PLAYER_STATS_DELETE = "player_stats_delete"

    # Dispatched after a player's stats have been edited
    PLAYER_STATS_EDITED = "player_stats_edited"


class Reason(StrEnum):
    MATCH_CANCELED_LOBBY_MOVE = "Match was canceled, moved back to lobby voice channel."
    MATCH_FINALISED_DEL_TEMP = "Match was finalised, temp channel no longer needed."
    MATCH_FINALISED_LOBBY_MOVE = "Match was finalised, moved back to lobby voice channel."
    TEAM_VC = "Automatically moved into team voice channel."
    VIEW_RESET_STATE = "Reset or cancel button was pressed on a match. Moved back to lobby voice channel."
    VC_DECONSTRUCT = "Temporary voice channel no longer needed."
