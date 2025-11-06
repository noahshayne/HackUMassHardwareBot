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


HOST=os.getenv("REDIS_HOST")

PORT = os.getenv("REDIS_PORT")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

REDIS_USERNAME = os.getenv("REDIS_USERNAME")

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD = os.getenv("DISCORD_GUILD")  # optional: a guild name to log

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
	if GUILD:
		guild = discord.utils.get(bot.guilds, name=GUILD)
		logging.info(f"Connected to guild: {guild}")

	# Try a Redis ping so auth/connection issues are obvious at startup.
	try:
		ok = r.ping()
		logging.info("Redis ping: %s", ok)
	except rexc.AuthenticationError as e:
		logging.warning("Redis auth failed. Check REDIS_USER/REDIS_PASSWORD. %s", e)
	except Exception as e:
		logging.warning("Redis connection check failed: %s", e)



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


def main() -> None:
	if not TOKEN:
	
		raise RuntimeError(
			"DISCORD_TOKEN not set."
		)
	bot.run(TOKEN)


if __name__ == "__main__":
	main()

