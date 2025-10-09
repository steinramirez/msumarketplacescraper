import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask

# Load environment variables from .env file
load_dotenv()

# Flask app for health checks (required for Render web service)
app = Flask(__name__)

@app.route('/')
def health_check():
    return {
        "status": "healthy",
        "last_interaction": time.time() - last_interaction,
        "timestamp": time.time()
    }

# Global variables for keep-alive
last_interaction = time.time()
keep_alive_interval = 59  # seconds (under 60 to prevent timeout)

def keep_alive():
    """Function to keep Render awake by simulating activity"""
    while True:
        time.sleep(keep_alive_interval)
        print("🔄 Keeping bot alive on Render...")

# Bot configuration
intents = discord.Intents.default()
# Remove message_content intent since we're using slash commands
# intents.message_content = True  # Not needed for slash commands
bot = commands.Bot(command_prefix='!', intents=intents)

# NFT data cache
nft_cache = {}
cache_timestamp = 0
CACHE_DURATION = 300  # 5 minutes

class NFTScraper:
    def __init__(self):
        self.base_url = "https://msu.io/marketplace/nft"
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.service = Service(ChromeDriverManager().install())
        self.chrome_options = chrome_options

    def scrape_nfts(self, search_term=None):
        """Scrape NFT data from the marketplace"""
        driver = None
        try:
            driver = webdriver.Chrome(service=self.service, options=self.chrome_options)

            # Use search URL if search term is provided
            if search_term:
                # URL encode the search term
                from urllib.parse import quote_plus
                encoded_term = quote_plus(search_term)
                url = f"{self.base_url}?keyword={encoded_term}"
                print(f"🔍 Searching URL: {url}")
            else:
                url = self.base_url
                print(f"📄 Loading general page: {url}")

            driver.get(url)

            # Wait for page to load
            time.sleep(5)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract NFT data
            nft_names = soup.find_all(class_="BaseCard_itemName__Z2GfD")
            nft_prices = soup.find_all(class_="CardPrice_number__OYpdb")

            print(f"📊 Found {len(nft_names)} names and {len(nft_prices)} prices")

            nfts = []
            for name, price in zip(nft_names, nft_prices):
                nfts.append({
                    'name': name.get_text().strip(),
                    'price': price.get_text().strip()
                })

            return nfts

        except Exception as e:
            print(f"Error scraping NFTs: {e}")
            return []
        finally:
            if driver:
                driver.quit()

async def get_nft_data():
    """Get NFT data with caching (async version)"""
    global nft_cache, cache_timestamp
    current_time = time.time()

    # Check if cache is still valid
    if current_time - cache_timestamp < CACHE_DURATION and nft_cache:
        return nft_cache

    # Scrape new data in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    scraper = NFTScraper()

    # Run the scraping in a thread executor to avoid event loop conflicts
    nft_cache = await loop.run_in_executor(None, scraper.scrape_nfts)
    cache_timestamp = current_time

    return nft_cache

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

    # Force sync slash commands to fix signature mismatches
    try:
        print('Syncing slash commands...')
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} command(s)')

        # List the synced commands
        for cmd in synced:
            print(f'  - /{cmd.name}')

    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

@bot.command(name='nft')
async def search_nft(ctx, *, search_term: str = None):
    """Search for NFTs by name"""
    global last_interaction
    last_interaction = time.time()

    await ctx.send("🔍 Fetching NFT data... This may take a moment.")

    nfts = await get_nft_data()

    if not nfts:
        await ctx.send("❌ Failed to fetch NFT data. Please try again later.")
        return

    if not search_term:
        # Show top 10 NFTs
        embed = discord.Embed(
            title="🏆 Top 10 NFTs by Price",
            color=0x00ff00
        )

        # Sort by price (convert to int for proper sorting)
        sorted_nfts = sorted(nfts, key=lambda x: int(x['price'].replace(',', '')), reverse=True)

        for i, nft in enumerate(sorted_nfts[:10], 1):
            embed.add_field(
                name=f"{i}. {nft['name']}",
                value=f"💰 {nft['price']}",
                inline=False
            )

        embed.set_footer(text=f"Total NFTs available: {len(nfts)}")
        await ctx.send(embed=embed)
        return

    # Search for specific NFT
    search_term = search_term.lower()
    matches = []

    for nft in nfts:
        if search_term in nft['name'].lower():
            matches.append(nft)

    if not matches:
        await ctx.send(f"❌ No NFTs found matching '{search_term}'")
        return

    # Limit to 10 results
    matches = matches[:10]

    embed = discord.Embed(
        title=f"🔍 Search Results for '{search_term}'",
        color=0x0099ff
    )

    for i, nft in enumerate(matches, 1):
        embed.add_field(
            name=f"{i}. {nft['name']}",
            value=f"💰 {nft['price']}",
            inline=False
        )

    if len(matches) == 10:
        embed.set_footer(text="Showing first 10 results")

    await ctx.send(embed=embed)

@bot.command(name='nftprice')
async def get_nft_price(ctx, *, nft_name: str):
    """Get the exact price of a specific NFT"""
    global last_interaction
    last_interaction = time.time()

    await ctx.send("🔍 Searching for NFT price...")

    nfts = await get_nft_data()

    if not nfts:
        await ctx.send("❌ Failed to fetch NFT data. Please try again later.")
        return

    nft_name = nft_name.lower()
    exact_match = None

    for nft in nfts:
        if nft['name'].lower() == nft_name:
            exact_match = nft
            break

    if exact_match:
        embed = discord.Embed(
            title=f"💰 {exact_match['name']}",
            description=f"**Price:** {exact_match['price']}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        # Try partial match
        partial_matches = [nft for nft in nfts if nft_name in nft['name'].lower()]

        if partial_matches:
            embed = discord.Embed(
                title=f"🔍 Similar NFTs found:",
                color=0xff9900
            )
            for nft in partial_matches[:5]:
                embed.add_field(
                    name=nft['name'],
                    value=f"💰 {nft['price']}",
                    inline=False
                )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ No NFT found with name '{nft_name}'")

@bot.command(name='nftstats')
async def nft_stats(ctx):
    """Get marketplace statistics"""
    global last_interaction
    last_interaction = time.time()

    await ctx.send("📊 Calculating marketplace statistics...")

    nfts = await get_nft_data()

    if not nfts:
        await ctx.send("❌ Failed to fetch NFT data. Please try again later.")
        return

    # Calculate statistics
    prices = [int(nft['price'].replace(',', '')) for nft in nfts]
    total_nfts = len(nfts)
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)

    # Find cheapest and most expensive NFTs
    cheapest = min(nfts, key=lambda x: int(x['price'].replace(',', '')))
    most_expensive = max(nfts, key=lambda x: int(x['price'].replace(',', '')))

    embed = discord.Embed(
        title="📊 MSU Marketplace Statistics",
        color=0x9932cc
    )

    embed.add_field(name="Total NFTs", value=f"{total_nfts:,}", inline=True)
    embed.add_field(name="Average Price", value=f"{avg_price:,.0f}", inline=True)
    embed.add_field(name="Price Range", value=f"{min_price:,} - {max_price:,}", inline=True)

    embed.add_field(
        name="💰 Cheapest NFT",
        value=f"{cheapest['name']}\n{cheapest['price']}",
        inline=False
    )

    embed.add_field(
        name="💎 Most Expensive NFT",
        value=f"{most_expensive['name']}\n{most_expensive['price']}",
        inline=False
    )

    embed.set_footer(text="Data refreshed every 5 minutes")
    await ctx.send(embed=embed)

@bot.command(name='help_nft')
async def help_nft(ctx):
    """Show available NFT commands"""
    global last_interaction
    last_interaction = time.time()

    embed = discord.Embed(
        title="🤖 NFT Bot Commands",
        description="Available commands for MSU Marketplace NFT data:",
        color=0x00ff00
    )

    embed.add_field(
        name="!nft",
        value="Show top 10 NFTs by price",
        inline=False
    )

    embed.add_field(
        name="!nft <search_term>",
        value="Search for NFTs by name",
        inline=False
    )

    embed.add_field(
        name="!nftprice <exact_name>",
        value="Get exact price of a specific NFT",
        inline=False
    )

    embed.add_field(
        name="!nftstats",
        value="Show marketplace statistics",
        inline=False
    )

    embed.add_field(
        name="!help_nft",
        value="Show this help message",
        inline=False
    )

    await ctx.send(embed=embed)

# Removed prefix commands - using only slash commands

# Slash Commands
@bot.tree.command(name="buscar", description="Buscar items NFT en el marketplace de MSU")
@app_commands.describe(nombre_item="Nombre del item que quieres buscar")
async def buscar(interaction: discord.Interaction, nombre_item: str):
    """Slash command to search for NFT items by name"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()  # Let Discord know we're processing

    # Use the scraper directly with search term in a thread
    loop = asyncio.get_event_loop()
    scraper = NFTScraper()
    try:
        matches = await loop.run_in_executor(None, scraper.scrape_nfts, nombre_item)
    except Exception as e:
        print(f"Error fetching NFT data: {e}")
        embed = discord.Embed(
            title="🔍 Resultados de búsqueda",
            description=f"Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)
        return

    if not matches:
        embed = discord.Embed(
            title="🔍 Resultados de búsqueda",
            description=f"No se encontraron items que coincidan con '{nombre_item}'",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)
        return

    # Sort by price (lowest first)
    matches = sorted(matches, key=lambda x: int(x['price'].replace(',', '')))

    # Show up to 15 results
    matches = matches[:15]

    # Calculate price statistics
    prices = [int(nft['price'].replace(',', '')) for nft in matches]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)

    embed = discord.Embed(
        title=f"🔍 Resultados para '{nombre_item}'",
        description=f"**{len(matches)}** item(s) encontrado(s)\n"
                   f"💰 Precio más bajo: **{min_price:,}**\n"
                   f"💰 Precio más alto: **{max_price:,}**\n"
                   f"💰 Precio promedio: **{avg_price:,.0f}**",
        color=0x00ff00
    )

    # Show items in price order (lowest to highest)
    for i, nft in enumerate(matches, 1):
        price_num = int(nft['price'].replace(',', ''))
        formatted_price = f"{price_num:,}"

        # Add price indicator
        if price_num == min_price:
            price_indicator = "🟢 (Más barato)"
        elif price_num == max_price:
            price_indicator = "🔴 (Más caro)"
        else:
            price_indicator = ""

        embed.add_field(
            name=f"{i}. {nft['name']}",
            value=f"💰 **{formatted_price}** {price_indicator}",
            inline=False
        )

    if len(matches) == 15:
        embed.set_footer(text="Mostrando los primeros 15 resultados (ordenados por precio)")
    else:
        embed.set_footer(text=f"Todos los resultados mostrados (ordenados por precio)")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="buscar_precio", description="Buscar items NFT ordenados por precio específico")
@app_commands.describe(
    nombre_item="Nombre del item que quieres buscar",
    orden="Orden de precios: 'barato' (más barato primero) o 'caro' (más caro primero)"
)
async def buscar_precio(interaction: discord.Interaction, nombre_item: str, orden: str = "barato"):
    """Search for NFT items with specific price ordering"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    # Use the scraper directly with search term in a thread
    loop = asyncio.get_event_loop()
    scraper = NFTScraper()
    try:
        matches = await loop.run_in_executor(None, scraper.scrape_nfts, nombre_item)
    except Exception as e:
        print(f"Error fetching NFT data: {e}")
        embed = discord.Embed(
            title="🔍 Resultados de búsqueda",
            description=f"Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)
        return

    if not matches:
        embed = discord.Embed(
            title="🔍 Resultados de búsqueda",
            description=f"No se encontraron items que coincidan con '{nombre_item}'",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)
        return

    # Sort by price based on user preference
    if orden.lower() in ["caro", "expensive", "high"]:
        matches = sorted(matches, key=lambda x: int(x['price'].replace(',', '')), reverse=True)
        sort_text = "más caros primero"
    else:
        matches = sorted(matches, key=lambda x: int(x['price'].replace(',', '')))
        sort_text = "más baratos primero"

    matches = matches[:15]

    # Calculate statistics
    prices = [int(nft['price'].replace(',', '')) for nft in matches]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)

    embed = discord.Embed(
        title=f"🔍 Resultados para '{nombre_item}' ({sort_text})",
        description=f"**{len(matches)}** item(s) encontrado(s)\n"
                   f"💰 Precio más bajo: **{min_price:,}**\n"
                   f"💰 Precio más alto: **{max_price:,}**\n"
                   f"💰 Precio promedio: **{avg_price:,.0f}**",
        color=0x0099ff
    )

    for i, nft in enumerate(matches, 1):
        price_num = int(nft['price'].replace(',', ''))
        formatted_price = f"{price_num:,}"

        embed.add_field(
            name=f"{i}. {nft['name']}",
            value=f"💰 **{formatted_price}**",
            inline=False
        )

    embed.set_footer(text=f"Ordenados por precio ({sort_text})")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="listar_items", description="Mostrar algunos items disponibles para búsqueda")
async def listar_items(interaction: discord.Interaction):
    """List some available items for search reference"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    try:
        nfts = await get_nft_data()
    except Exception as e:
        print(f"Error fetching NFT data: {e}")
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    if not nfts:
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    # Get some sample items
    sample_items = nfts[:20]  # First 20 items

    embed = discord.Embed(
        title="📋 Algunos items disponibles",
        description="Aquí tienes algunos ejemplos de items que puedes buscar:",
        color=0x0099ff
    )

    for i, nft in enumerate(sample_items, 1):
        embed.add_field(
            name=f"{i}. {nft['name']}",
            value=f"💰 {nft['price']}",
            inline=True
        )

    embed.set_footer(text=f"Total de items disponibles: {len(nfts)}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="top_nfts", description="Mostrar los 10 NFTs más caros del marketplace")
async def top_nfts(interaction: discord.Interaction):
    """Slash command to show top 10 most expensive NFTs"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    try:
        nfts = await get_nft_data()
    except Exception as e:
        print(f"Error fetching NFT data: {e}")
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    if not nfts:
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    # Sort by price (highest first)
    sorted_nfts = sorted(nfts, key=lambda x: int(x['price'].replace(',', '')), reverse=True)

    embed = discord.Embed(
        title="🏆 Top 10 NFTs más caros",
        description="Los items más valiosos del marketplace:",
        color=0xffd700
    )

    for i, nft in enumerate(sorted_nfts[:10], 1):
        price_num = int(nft['price'].replace(',', ''))
        formatted_price = f"{price_num:,}"

        embed.add_field(
            name=f"{i}. {nft['name']}",
            value=f"💰 **{formatted_price}**",
            inline=False
        )

    embed.set_footer(text=f"Total de NFTs disponibles: {len(nfts)}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="estadisticas", description="Mostrar estadísticas del marketplace")
async def estadisticas(interaction: discord.Interaction):
    """Slash command to show marketplace statistics"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    try:
        nfts = await get_nft_data()
    except Exception as e:
        print(f"Error fetching NFT data: {e}")
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    if not nfts:
        await interaction.followup.send("❌ Error al obtener datos de NFT. Por favor intenta de nuevo más tarde.")
        return

    # Calculate statistics
    prices = [int(nft['price'].replace(',', '')) for nft in nfts]
    total_nfts = len(nfts)
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)

    # Find cheapest and most expensive NFTs
    cheapest = min(nfts, key=lambda x: int(x['price'].replace(',', '')))
    most_expensive = max(nfts, key=lambda x: int(x['price'].replace(',', '')))

    embed = discord.Embed(
        title="📊 Estadísticas del Marketplace MSU",
        description="Información general del marketplace:",
        color=0x9932cc
    )

    embed.add_field(name="Total de NFTs", value=f"{total_nfts:,}", inline=True)
    embed.add_field(name="Precio Promedio", value=f"{avg_price:,.0f}", inline=True)
    embed.add_field(name="Rango de Precios", value=f"{min_price:,} - {max_price:,}", inline=True)

    embed.add_field(
        name="💰 NFT más barato",
        value=f"**{cheapest['name']}**\n{int(cheapest['price'].replace(',', '')):,}",
        inline=False
    )

    embed.add_field(
        name="💎 NFT más caro",
        value=f"**{most_expensive['name']}**\n{int(most_expensive['price'].replace(',', '')):,}",
        inline=False
    )

    embed.set_footer(text="Datos actualizados cada 5 minutos")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="clear_sync", description="Limpiar y sincronizar comandos (arregla errores)")
async def clear_sync_slash(interaction: discord.Interaction):
    """Slash command to clear and sync commands"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    try:
        # Clear all commands first
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()

        # Re-sync with current commands
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Comandos limpiados y sincronizados: {len(synced)} comando(s)\n" + "\n".join([f"- /{cmd.name}" for cmd in synced]))
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="sync_commands", description="Sincronizar comandos slash")
async def sync_commands_slash(interaction: discord.Interaction):
    """Slash command to sync commands"""
    global last_interaction
    last_interaction = time.time()

    await interaction.response.defer()

    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Sincronizados {len(synced)} comando(s):\n" + "\n".join([f"- /{cmd.name}" for cmd in synced]))
    except Exception as e:
        await interaction.followup.send(f"❌ Error al sincronizar: {e}")

# Run the bot
if __name__ == "__main__":
    # Get bot token from environment variable
    bot_token = os.getenv('DISCORD_TOKEN')

    if not bot_token:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please make sure you have a .env file with your bot token.")
        exit(1)

    print("🤖 Starting Discord bot...")

    # Start Flask web server thread for health checks
    port = int(os.getenv('PORT', 10000))
    flask_thread = threading.Thread(target=lambda: app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False), daemon=True)
    flask_thread.start()
    print(f"🌐 Health check server started on port {port}")

    # Start keep-alive thread for Render
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()

    bot.run(bot_token)
