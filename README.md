# The Construct

Queueing, drafting, and ranking all in one place.

## Getting Started

Setting up the bot to work with your server is very simple. The following instructions assume you have the `Manage Server` permission.
All of the bot's commands have descriptive text in the Discord client, or you can use `/help` to get command usage information.

### Invite

Use this [invite link](https://discord.com/oauth2/authorize?client_id=1470118099150704913) to invite the bot. It already has necessary
permissions pre-selected.

### Season Management

In order to start matches, the server must have an active season (used to isolate seasonal stats and player rankings).
To do so, enter the command `/season start` and follow the prompts.

| Command         | Description                     | Notes                               |
|-----------------|---------------------------------|-------------------------------------|
| `/season start` | Starts a new season             | Requires `Manage Server` permission |
| `/season stop`  | Stops the current active season | Requires `Manage Server` permission |

### Queue Management

Queues may be created at any time, even without an active season. Up to 20 queues can be created at a time per server.

| Command                       | Description                                                  | Notes                                                                                                  |
|-------------------------------|--------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `/queue create [type] [name]` | Create a queue of the specified type with the specified name | Any user is able to create a queue                                                                     |
| `/queue delete [name]`        | Delete a queue with the specified name                       | Only the queue owner may perform this operation                                                        |
| `/queue join [name]`          | Join a queue with the specified name                         | This operation may only be done while the queue is unlocked and no match is in progress for said queue |
| `/queue leave [name]`         | Leave a queue you have previously joined                     | This operation may only be done while the queue is unlocked and no match is in progress for said queue |
| `/queue lock [name]`          | Lock a queue with the specified name                         | Only the queue owner may perform this operation                                                        |
| `/queue unlock [name]`        | Unlock a queue with the specified name                       | Only the queue owner may perform this operation                                                        |
| `/queue list`                 | Lists all active queues in the server                        |                                                                                                        |

### Match Management

A match can be started once a queue has two or more players in it.

| Command        | Description                                  | Notes                                                                      |
|----------------|----------------------------------------------|----------------------------------------------------------------------------|
| `/match start` | Start a match using the prematch setup modal | Anyone can start a match so long as they are the owner of startable queues |

### Player Stats Management

Server administrators can directly manipulate player statistics in order to perform
corrections or adjustments whenever necessary.

| Command                | Description                                             | Notes                               |
|------------------------|---------------------------------------------------------|-------------------------------------|
| `player reset [name]`  | Resets stats for a player in the current active season  | Requires `Manage Server` permission |
| `player delete [name]` | Deletes stats for a player in the current active season | Requires `Manage Server` permission |
| `player edit [name]`   | Edits stats for a player in the current active season   | Requires `Manage Server` permission |

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

### 2.1.0-beta

#### Added

- Introduction of advanced player ranking system powered internally by [OpenSkill](https://openskill.me/en/stable/)
  - Implement auto draft feature based on player skill
  - Leaderboard rankings based on OpenSkill ordinal
  - Win predictions appear on the match panel
- UI/UX overhaul
  - Prematch configuration now happens in an interactive message instead of a modal
  - Added auto draft and map pool selection
  - Match panel responsiveness increased by performing frontend operations first (editing text content),
  enabling/disabling buttons, etc
  - During team-specific voice channel teardown, all members connected to those voice channels will get moved,
  regardless of whether or not they were an actual match participant or spectator
- Added bot settings
  - Configuration of bot administrators, bound text channel, and map pools
  - Server owner can specify bot administrators that will inherit a similar permission level
- Bot administrators
  - Bot admainistrators can perform operations previously only limited to the queue owner and team captains,
  such as MVP designation, results reporting, match panel reset, match panel cancel, etc.
  - Bot administrators can perform management operations without requiring ownership of individual managed items,
  like queue state, match starting, etc.
- Bound text channel
  - No need to specify what text channel the match thread will spawn in, instead bot administrators can set this
  beforehand
- Custom map pools
  - Specify the larger set of maps the bot will choose from when a match is started
  - Each server can have up to 10 custom map pools
  - Bot admins can create, edit, and delete custom map pools

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
- If the player was banned, delete their stat entry from the current season, if one exists
- Prevent a single failure to send a prematch DM to a player from causing all remaining players to not get the prematch DM

### 1.0.0-beta

- Initial release
