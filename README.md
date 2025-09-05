# MSU Marketplace NFT Discord Bot

A Discord bot that scrapes and provides real-time NFT data from the MSU marketplace.

## Features

- 🔍 Search NFTs by name
- 💰 Get exact NFT prices
- 📊 View marketplace statistics
- 🏆 Show top NFTs by price
- ⚡ Cached data for fast responses (5-minute cache)

## Commands

### Slash Commands
- `/buscar <nombre_item>` - Buscar items NFT por nombre (ordenados por precio)
- `/buscar_precio <nombre_item> [orden]` - Buscar con orden específico (barato/caro)
- `/listar_items` - Mostrar algunos items disponibles para búsqueda
- `/top_nfts` - Mostrar los 10 NFTs más caros
- `/estadisticas` - Mostrar estadísticas del marketplace
- `/sync_commands` - Sincronizar comandos
- `/clear_sync` - Limpiar y sincronizar comandos (arregla errores)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a Discord bot:
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token
   - **Important**: The bot uses default intents only (no privileged intents required)

3. Create a `.env` file with your bot token:
   - Copy `env_example.txt` to `.env`
   - Replace `your_discord_bot_token_here` with your actual bot token
   - Example `.env` file:
   ```
   DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWx
   CLIENT_ID=1234567890123456789
   ```

4. Invite the bot to your server:
   - Go to OAuth2 > URL Generator
   - Select "bot" and "applications.commands" scopes
   - Select necessary permissions (Send Messages, Embed Links, Use Slash Commands, etc.)
   - Use the generated URL to invite the bot

5. Run the bot:
```bash
python discord_bot.py
```

## How it works

The bot uses Selenium to scrape the MSU marketplace NFT page, extracting:
- NFT names (class: `BaseCard_itemName__Z2GfD`)
- NFT prices (class: `CardPrice_number__OYpdb`)

Data is cached for 5 minutes to avoid excessive scraping and provide fast responses.

## Example Usage

### Slash Commands
```
/buscar unchained dagger
/buscar_precio unchained dagger barato
/buscar_precio unchained dagger caro
/listar_items
/top_nfts
/estadisticas
/clear_sync
```

## Notes

- The bot runs in headless Chrome mode
- Data is refreshed every 5 minutes
- ChromeDriver is automatically managed by webdriver-manager
- All commands return formatted Discord embeds for better readability
- **Important**: Never commit your `.env` file to version control - it contains sensitive information
- The bot will automatically load your token from the `.env` file

## Troubleshooting

### Bot won't start - Privileged Intents Error
If you get an error about privileged intents:
- The bot is configured to use default intents only
- No special permissions are required in the Discord Developer Portal
- Make sure your bot token is correct in the `.env` file

### Slash Commands not appearing
- Commands may take up to 1 hour to appear globally
- Use `/sync_commands` (admin only) to force sync commands
- Make sure your bot has "Use Slash Commands" permission in your server

### Command Signature Mismatch Error
If you get a "CommandSignatureMismatch" error:
- Use `/clear_sync` to clear old commands and re-sync
- Use `/sync_commands` to manually sync
- Restart the bot if problems persist
- This usually happens when Discord has cached old command versions
