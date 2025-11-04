from __future__ import annotations

import logging
import os
# pathlib not needed for simple dotenv loading
from dotenv import load_dotenv

import discord
from discord.ext import commands

# Load environment variables from a .env file (if present).

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD = os.getenv("DISCORD_GUILD")  # optional: a guild name to log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")

intents = discord.Intents.default()
# Allow reading message content for simple command handling. Ensure your bot has the message content intent enabled.
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
	logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")
	if GUILD:
		guild = discord.utils.get(bot.guilds, name=GUILD)
		logging.info(f"Connected to guild: {guild}")


@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
	"""Responds with Pong! to test the bot is alive."""
	await ctx.send("Pong!")


def main() -> None:
	if not TOKEN:
	
		raise RuntimeError(
			"DISCORD_TOKEN not set."
		)
	bot.run(TOKEN)


if __name__ == "__main__":
	main()

