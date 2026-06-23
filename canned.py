from enum import StrEnum


class Canned(StrEnum):
    """I am too lazy to type everything out and ensure every instance
    of repeated text is exactly the same, so every bit of static text
    is mapped to here.

    Format:
    (PREFIX)_[COG/VIEW/MODAL/FUNCTION]_[DESCRIPTOR]

    Prefixes:
    ERR         - Used to designate an error message
    (no prefix) - Used to designate a confirmation or success message
    """

    # Deprecation Warnings
    DEPR_V1X_POINTS = "Support for v1.x points rating has been deprecated. Use the v2.x+ OpenSkill ratings instead."

    # General
    ERR_PERMS = "ERROR - You do not have permission to run this command"
    ERR_BOT_USER = "ERROR - This operation cannot be done on bot users"
    ERR_COOLDOWN = "ERROR - The command is on cooldown for another `{}`s"

    # Queues
    ERR_QUEUE_EXISTS = "ERROR - A queue already exists with the specified name"
    ERR_QUEUE_NO_EXISTS = "ERROR - No queue exists with the specified name"
    ERR_QUEUE_NAME_LEN = (
        "ERROR - The specified name must be no longer than 100 characters"
    )
    ERR_QUEUE_LIMIT = "ERROR - This server has reached the 20 simultaneous queues limit and cannot create more queues at this time"
    ERR_QUEUE_OWNER = (
        "ERROR - Unable to modify the specified queue, as you are not its owner"
    )
    ERR_QUEUE_ALREADY_IN = "ERROR - You are already in the specified queue"
    ERR_QUEUE_NOT_IN = "ERROR - You are not in the specified queue"
    ERR_QUEUE_FULL = (
        "ERROR - The queue you are attempting to join is full, unable to join"
    )
    ERR_QUEUE_LOCKED_JOIN = "ERROR - The queue you are attempting to join is locked and cannot accept new players at this time"
    ERR_QUEUE_LOCKED_LEAVE = "ERROR - The queue you are attempting to leave is locked. You cannot leave at this time"
    ERR_QUEUE_LOCKSTATE_L = "ERROR - The specified queue is already locked"
    ERR_QUEUE_LOCKSTATE_U = "ERROR - The specified queue is already unlocked"
    ERR_QUEUE_PROGSTATE = "ERROR - The specified queue currently has a match in progress and cannot be modified"
    ERR_QUEUE_NO_LIST_RESULTS = (
        "ERROR - Could not find any queues matching the specified criteria"
    )

    # R6 Prematch
    ERR_PREMATCH_NO_QUEUE = "ERROR - Please specify a queue"
    ERR_PREMATCH_NO_VC = "ERROR - Please specify a voice channel"
    ERR_PREMATCH_MANUAL_CAPTAIN = "ERROR - Please specify two captains when the captain selection mode is set to manual"
    ERR_PREMATCH_BOT_USER = "ERROR - Cannot designate a bot user as captain"
    ERR_PREMATCH_INVALID_USER = (
        "ERROR - Cannot designate a user as captain is they are not in the player list"
    )

    # Matches
    ERR_MATCH_START_QUEUES = "ERROR - Unable to start a match, as you are not the owner of any startable queues"
    ERR_MATCH_START_NO_TC_BOUND = "ERROR - Unable to start a match, as the text channel for creating the thread has not been bound"
    ERR_MATCH_START_INVALID_TC = "ERROR - Unable to start a match, as the currently bound text channel was unable to be found"
    ERR_MATCH_IN_PROGRESS = "ERROR - This match is already in progress"
    ERR_MATCH_SEASON = "ERROR - There is no active season in this server. Create an active season with `/season start`"
    MATCH_DM_CONF = (
        "Players will receive a match start notification in their DMs shortly"
    )

    # Seasons
    ERR_SEASON_EXISTS = "ERROR - An active season already exists for this server"
    ERR_SEASON_NO_EXISTS = "ERROR - No active season was found for this server"
    ERR_SEASON_MIP = "ERROR - There are currently active matches in this server. Please finish them before attempting to stop the current season"
    ERR_SEASON_DUPLICATE_NAME = (
        "ERROR - The specified name has already been used for a previous season"
    )
    SEASON_STOP = "The current season has been stopped and rankings have been finalised"
    SEASON_STOP_DM_CONF = "All players who participated in the current season have been sent their season recaps in their DMs"

    # Seasons - General Errors
    ERR_SEASON_GEN_START = "ERROR - An error has occurred. Unable to start a season"

    # Stats
    ERR_STATS_NO_PLAYERS = (
        "ERROR - No players are currently ranked in this server for this season"
    )
    ERR_STATS_PLAYER_NO_RANKED = (
        "ERROR - The specified player is not currently ranked for this season"
    )
    ERR_STATS_INVALID_SEASON_NAME = (
        "ERROR - Could not find a season with the specified name"
    )
    ERR_STATS_PLAYER_EDIT = "ERROR - All values must be integers"

    # Settings
    ERR_SETTINGS_SELECTION_GEN = "ERROR - Could not choose a setting"
    ERR_SETTINGS_SET_ADMIN = "ERROR - Could not set bot administrators"
    ERR_SETTINGS_BIND_CHANNEL = "ERROR - Could not bind a text channel"
    ERR_SETTINGS_BIND_CHANNEL_PERMS = "ERROR - Bot does not have permission to create private threads in the selected text channel"
    ERR_SETTINGS_CREATE_MAP_POOL = "ERROR - Could not create a custom map pool"
    ERR_SETTINGS_CREATE_MAP_POOL_NAME = (
        "ERROR - Please give the map pool a different name"
    )
    ERR_SETTINGS_MAP_POOL_MANAGE_NO_NAME = (
        "ERROR - Please specify a map pool using the selector"
    )
    ERR_SETTINGS_MAP_POOL_NAME_TAKEN = "ERROR - The specified name is already in use"
    ERR_SETTINGS_MAP_POOL_CAP = (
        "ERROR - This server has reached the limit for the amount of custom map pools"
    )

    # Feedback
    FEEDBACK_CONF = "Thank you. Your feedback has been sent to the developers"

    # R6 Prematch - General Errors
    ERR_R6PRE_GEN = "ERROR - An error has occurred. Unable to start match"

    # R6 Draft
    ERR_R6DRAFT_OWNER_OR_ADMIN = (
        "ERROR - Only the queue owner or admin can execute this"
    )
    ERR_R6DRAFT_CAPTAIN = "ERROR - Only a team captain can execute this"
    ERR_R6DRAFT_NO_DRAFT = "ERROR - There are no players available to draft"
    ERR_R6DRAFT_DRAFT_TURN = "ERROR - It is not your turn to draft players"
    ERR_R6DRAFT_BAN_TURN = "ERROR - It is not your turn to ban maps"
    ERR_R6DRAFT_SIDE = "ERROR - Your team cannot select the starting sides"
    ERR_R6DRAFT_MVP_EXISTS = "ERROR - You have already designated an MVP for your team"
    ERR_R6DRAFT_FINAL = (
        "ERROR - The match results have been finalised and cannot be modified"
    )
    ERR_R6DRAFT_ROUNDS_WON_TYPE = (
        "ERROR - Rounds won must be two unique integers greater than or equal to zero"
    )
    ERR_R6DRAFT_ROUNDS_WON_MISMATCH = "ERROR - Please ensure the rounds won for the winning team is greater than that of the losing team"
    R6DRAFT_MATCH_CANCEL = "This match has been canceled by the queue owner. Your rankings remain unchanged"
    R6DRAFT_RESET_DEFAULT = (
        "Player draft, map bans, and starting side selection have been reset"
    )
    R6DRAFT_DISCLAIMER = "-# *Only team captains and the queue owner can interact with the buttons below*"
    R6DRAFT_THREAD_CLEANUP = "Match contained within thread was finalised or canceled"
    R6DRAFT_VC_CREATION = "Voice channels are being created for each team, and players will be moved to their appropriate voice channel momentarily"

    # R6 Draft - General Errors
    ERR_R6DRAFT_GEN_DRAFT = "ERROR - An error has occurred. Unable to draft player"
    ERR_R6DRAFT_GEN_BAN = "ERROR - An error has occurred. Unable to ban map"
    ERR_R6DRAFT_GEN_SIDE = (
        "ERROR - An error has occurred. Unable to select starting side"
    )
    ERR_R6DRAFT_GEN_MVP = "ERROR - An error has occurred. Unable to designate team MVP"
    ERR_R6DRAFT_GEN_RES = (
        "ERROR - An error has occurred. Unable to report match results"
    )
