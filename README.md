# The Construct

Queueing, drafting, and ranking all in one place.

## Getting Started

Setting up the bot to work with your server is very simple. The following
instructions assume you have the `Manage Server` permission. All of the bot's
commands have descriptive text in the Discord client, or you can use `/help` to
get command usage information.

### Invite

Use this [invite link](https://discord.com/oauth2/authorize?client_id=1470118099150704913)
to invite the bot. It already has necessary permissions pre-selected.

### Settings

There are a few settings that must be configured in order for the bot to work
properly when it joins a server. Initial configuration must be done by the server
owner, but after bot administrators are assigned, such settings may be changed
by those designated users as well.

| Command     | Description                        | Notes                                                                                          |
|-------------|------------------------------------|------------------------------------------------------------------------------------------------|
| `/settings` | Shows an interactive settings view | In order to make modifications, users must be the server owner or designated bot administrator |

| Setting              | Description                                                                                  | Default                                                                    | Required |
|----------------------|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|----------|
| `Bot Administrators` | Delegate bot administrator permissions to up to 5 additional users                           | Nobody (server owner is implicit)                                          | No       |
| `Bound Text Channel` | Text channel in which match-related threads are spawned in                                   | Unset                                                                      | Yes      |
| `Custom Map Pools`   | Has its own page, allows for creation, editing, and deleting custom map pools for the server | Unset (default ranked and quickmatch map pools cannot be viewed or edited) | No       |

### Season Management

In order to start matches, the server must have an active season (used to isolate
seasonal stats and player rankings). To do so, enter the command `/season start`
and follow the prompts.

| Command         | Description                        | Notes                                                             |
|-----------------|------------------------------------|-------------------------------------------------------------------|
| `/season start` | Starts a new season                | User must be a bot administrator in order to perform this command |
| `/season stop`  | Stops the current active season    | User must be a bot administrator in order to perform this command |
| `season list`   | Lists all current and past seasons |                                                                   |

### Queue Management

Queues may be created at any time, even without an active season. Up to 20 queues
can exist concurrently per server, and upon match completion, the corresponding
queue entry is destroyed.

| Command         | Description                                                          | Notes                                                                                                                       |
|-----------------|----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `/queue create` | Opens an interactive panel for individual queue creation             | Any user is able to create a queue                                                                                          |
| `/queue delete` | Opens an interactive panel for individual queue deletion             | Only the queue owner or bot administrators may perform this operation                                                       |
| `/queue join`   | Opens an interactive panel for multiple simultaneous queue joining   | This operation may only be done while no match is in progress or locked for the selected queues                             |
| `/queue leave`  | Opens an interactive panel for multiple simultaneous queue leaving   | This operation may only be done while no match is in progress or locked for the selected queues                             |
| `/queue lock`   | Opens an interactive panel for multiple simultaneous queue locking   | Only the queue owner or bot administrators may perform this operation while no match is in progress for the selected queues |
| `/queue unlock` | Opens an interactive panel for multiple simultaneous queue unlocking | Only the queue owner or bot administrators may perform this operation while no match is in progress for the selected queues |
| `/queue list`   | Lists all active queues in the server                                |                                                                                                                             |

### Match Management

A match can be started once a queue has two or more players in it.

| Command        | Description                                  | Notes                                                                                                |
|----------------|----------------------------------------------|------------------------------------------------------------------------------------------------------|
| `/match start` | Start a match using the prematch setup modal | Anyone can start a match so long as they are the owner of startable queues or are bot administrators |

### Player Stats Management

Bot administrators may reset or delete player stats for the given queue type in
the current active season.

| Command                       | Description                                             | Notes                                                                  |
|-------------------------------|---------------------------------------------------------|------------------------------------------------------------------------|
| `player reset [name] [type]`  | Resets stats for a player in the current active season  | Only the server owner or bot administrators may perform this operation |
| `player delete [name] [type]` | Deletes stats for a player in the current active season | Only the server owner or bot administrators may perform this operation |

### Leaderboard

Access leaderboards for current or previous seasons.

| Command               | Description                                              | Notes                                                                           |
|-----------------------|----------------------------------------------------------|---------------------------------------------------------------------------------|
| `/leaderboard (name)` | View an interactive leaderboard for the specified season | If the season name is unspecified, it will default to the current active season |

### Feedback

Give feedback directly to the developers.

| Command     | Description                            | Notes                                               |
|-------------|----------------------------------------|-----------------------------------------------------|
| `/feedback` | Submit feedback via the feedback modal | There is a per-user cooldown of `300`s between uses |

## Changelog

### 2.1.3-beta

This patch introduces a small feature addition to the drafting process.

#### Added
- Option to finalise your team's draft early and give the rest of the players
in the draft pool to the other team
  - This option will only appear when the amount of players left in the draft
  pool (excluding your selection) is less than or equal to the remaining player
  slots available in the other team

### 2.1.2-beta

This patch release reworks the majority of the queue-related commands, providing
an improved user experience while making it harder for users to accidentally 
submit invalid responses.

#### Added

- Modal-based UI for user input for the following queue-related commands:
  - `/queue create`
  - `/queue delete`
  - `/queue join`
  - `/queue leave`
  - `/queue lock`
  - `/queue unlock`

#### Bugfixes

- Allow bot administrators to delete queues in addition to just the queue owner
- Signifncantly reduce end user capability to submit malformed/invalid input into the
QueueManager backend for processing
  - Cases where this can happen are uncommon race conditions on the human timescale,
  such as an administrator deleting a queue after a user uses `/queue join`, but before
  the user submits their response

### 2.1.1-beta

This patch release is targeted at a few important bugs related to how the bot
handles situations where it softlocks any individual match waiting for user input
that will never arrive.

#### Bugfixes

- Created a monitoring system for currently active match interactive panels
  - Prior to this release, if a user were to delete the match panel before the
  match was gracefully finished (either by reporting all MVP/results or cancellation),
  the match entry would remain in limbo, preventing any subsequent queues from
  using that name and preventing any attempts to end the current season
  - Now, match panel message IDs are tracked and the panel will be recreated
  if its message is deleted, while preserving the state of the draft/bans/side select
- Actually check bound text channel send messages in threads permission for the bot
before the `/match start` command is fully processed, as well as during submission
of the prematch configuration interactive panel
  - Prior to this release, the bot would lock the queue and create the match entry,
  but would fail to display anything in the created thread and softlock the queue
  and match entry, causing similar effects as the above bug related to message
  deletion
  - Now, starting the match will not be possible if the bot does not have adequate
  permissions to send message in threads spawned in the bound text channel

### 2.1.0-beta

#### Added

- Introduction of advanced player ranking system powered internally by
[OpenSkill](https://openskill.me/en/stable/)
  - Implement auto draft feature based on player skill
  - Leaderboard rankings based on OpenSkill ordinal
  - Win predictions appear on the match panel
- UI/UX overhaul
  - Prematch configuration now happens in an interactive message instead of a modal
  - Added auto draft and map pool selection
- Added bot settings
  - Configuration of bot administrators, bound text channel, and map pools
  - Server owner can specify bot administrators that will inherit a similar
  permission level
- Bot administrators
  - Bot administrators can perform operations previously only limited to the
  queue owner and team captains, such as MVP designation, results reporting,
  match panel reset, match panel cancel, etc.
  - Bot administrators can perform management operations without requiring
  ownership of individual managed items, like queue state, match starting, etc.
- Bound text channel
  - No need to specify what text channel the match thread will spawn in, instead
  bot administrators can set this beforehand
- Custom map pools
  - Specify the larger set of maps the bot will choose from when a match is started
  - Each server can have up to 10 custom map pools
  - Bot admins can create, edit, and delete custom map pools

#### Bugfixes

- Match panel responsiveness increased by performing frontend operations first
  (editing text content), enabling/disabling buttons, etc
- During team-specific voice channel teardown, all members connected to those
voice channels will get moved, regardless of whether or not they were an actual
match participant or spectator
- Prevent a `discord.HTTPException` while sending season recap DMs from stopping
the bot from sending the DMs to subsequent players

#### Removed

- Deprecation of legacy v1.x points-based player ranking system
- Modal-based prematch configuration

### 2.0.0-beta

#### Added

- Separation of leadearboards by queue type

### 1.0.1-beta

#### Added

- When a player leaves a server, remove them from any queues they are currently in
  - This includes locked queues, so long as the queue is not in progress
- If the player was banned, delete their stat entry from the current season, if
one exists
- Prevent a single failure to send a prematch DM to a player from causing all
remaining players to not get the prematch DM

### 1.0.0-beta

- Initial release
