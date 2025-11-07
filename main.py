from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv
import redis
import redis.exceptions as rexc

import discord
from discord.ext import commands
from discord import app_commands

# Load environment variables from a .env file (if present) before reading them.
load_dotenv()

# Configure Redis client from environment (defaults provided for convenience).


HOST = os.getenv("REDIS_HOST")
PORT_STR = os.getenv("REDIS_PORT")
try:
	PORT = int(PORT_STR)
except ValueError:
	raise RuntimeError(f"Invalid REDIS_PORT value: {PORT_STR!r}. Must be an integer.")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_USERNAME = os.getenv("REDIS_USERNAME") 

TOKEN = os.getenv("DISCORD_TOKEN")

HARDWARE_LIST_URL = "https://docs.google.com/spreadsheets/d/1kKcwllyCGzlzySMMyQ6V-yhySCRb5-mZsAYSeL_Y_VE/edit?gid=0#gid=0"   #public hardware url link

if not HOST:
	raise RuntimeError(
		"REDIS_HOST is not set. Set REDIS_HOST, REDIS_PORT, REDIS_USERNAME, and REDIS_PASSWORD in your environment or .env."
	)

r = redis.Redis(
	host=HOST,
	port=PORT,
	decode_responses=True,
	username=REDIS_USERNAME,
	password=REDIS_PASSWORD,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")

intents = discord.Intents.default()
# Message Content is a privileged intent; enable only via env if needed for legacy prefix commands.
if os.getenv("DISCORD_MESSAGE_CONTENT", "false").lower() in ("1", "true", "yes"):
	intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



@bot.event
async def on_ready() -> None:
	logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")
	# Sync app commands
	guild_id = os.getenv("DISCORD_GUILD_ID") #server id
	try:
		if guild_id:
			gobj = discord.Object(id=int(guild_id))
			# Copy global command definitions into the guild and sync.
			bot.tree.copy_global_to(guild=gobj)
			cmds = await bot.tree.sync(guild=gobj)
			logging.info("Synced %d app commands to guild ID %s (instant)", len(cmds), guild_id)
		else:
			cmds = await bot.tree.sync()
			logging.info("Synced %d global app commands (may take up to ~1 hour)", len(cmds))
	except Exception as e:
		logging.warning("Failed to sync app commands: %s", e)



# ---- Slash command: /inventory ----
async def _scan_keys(prefix: str, limit: int = 25) -> list[str]:
	"""Return up to `limit` keys matching the given prefix, case-insensitively."""
	low = prefix.lower() if prefix else ""

	def _scan() -> list[str]:
		found: list[str] = []
		for k in r.scan_iter(match="*", count=200):  # scan broadly, filter locally
			if not low or k.lower().startswith(low):
				found.append(k)
				if len(found) >= limit:
					break
		return found

	return await asyncio.to_thread(_scan)


@app_commands.autocomplete(item=lambda i, c: asyncio.create_task(_inventory_autocomplete(i, c)))
async def _inventory_autocomplete(interaction: discord.Interaction, current: str):
	try:
		keys = await _scan_keys(current, limit=25)
	except Exception:
		keys = []
	# Return up to 25 choices
	return [app_commands.Choice(name=k, value=k) for k in keys]


@bot.tree.command(name="inventory", description="Get the inventory count of the item")
@app_commands.describe(item="Inventory item key")
@app_commands.autocomplete(item=_inventory_autocomplete)
async def inventory(interaction: discord.Interaction, item: str):
	if not item:
		await interaction.response.send_message("Please select an inventory item.", ephemeral=True)
		return
	try:
		# Fetch the first element of the list for this key
		val = r.lindex(item, 0)
		if val is None:
			# Key missing, empty list, or wrong type. Try to provide a helpful hint.
			try:
				ktype = r.type(item)
			except Exception:
				ktype = "unknown"
			if ktype == "string":
				sval = r.get(item)
				await interaction.response.send_message(f"{item}: {sval}")
			else:
				await interaction.response.send_message(
					f"No list value found at '{item}'. It may be missing, empty, or not a list.",
					ephemeral=True,
				)
			return
		await interaction.response.send_message(f"{item}: {val}")
	except rexc.AuthenticationError:
		await interaction.response.send_message(
			"Redis authentication failed. Set REDIS_USER and REDIS_PASSWORD in your .env to match your provider.",
			ephemeral=True,
		)
	except Exception as e:
		await interaction.response.send_message(f"Error reading '{item}': {e}", ephemeral=True)


@bot.tree.command(name="hardwarelist", description="Get the hardware inventory link")
async def hardwarelist(interaction: discord.Interaction):
	"""Sends a link to the hardware inventory/resource list."""
	await interaction.response.send_message(HARDWARE_LIST_URL)


def main() -> None:
	if not TOKEN:
	
		raise RuntimeError(
			"DISCORD_TOKEN not set."
		)
	bot.run(TOKEN)


if __name__ == "__main__":
	main()

