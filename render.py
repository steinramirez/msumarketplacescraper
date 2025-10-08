from discord_bot import bot
import os

if __name__ == "__main__":
    bot_token = os.getenv('DISCORD_TOKEN')

    if not bot_token:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        exit(1)

    print("🤖 Starting Discord bot on Render...")
    bot.run(bot_token)
