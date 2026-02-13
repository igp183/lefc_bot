import json
from datetime import time
from pathlib import Path
from typing import Optional

import discord
import feedparser
from discord import app_commands
from discord.ext import commands, tasks

QUANTA_RSS = "https://api.quantamagazine.org/feed/"
CONFIG_PATH = Path("data/news_config.json")
# Post daily at 09:00 UTC (10:00 in Portugal during winter, 10:00 during summer)
DAILY_POST_TIME = time(hour=9, minute=0)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


class News(commands.Cog):
    """Daily news about Quanta Magazine"""

    emoji = "📰"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_config()
        self.last_posted_url: Optional[str] = self.config.get("last_posted_url")

    async def cog_load(self):
        self.daily_news.start()

    async def cog_unload(self):
        self.daily_news.cancel()

    # RSS fetching

    def _fetch_articles(self, limit: int = 5) -> list[dict]:
        """Fetch latest articles from Quanta Magazine RSS."""
        feed = feedparser.parse(QUANTA_RSS)
        articles = []
        for entry in feed.entries[:limit]:
            # Try to get the thumbnail image
            image_url = None
            if hasattr(entry, "media_content"):
                for media in entry.media_content:
                    if "image" in media.get("type", ""):
                        image_url = media["url"]
                        break
            if not image_url and hasattr(entry, "media_thumbnail"):
                for thumb in entry.media_thumbnail:
                    image_url = thumb.get("url")
                    break

            articles.append(
                {
                    "title": entry.get("title", "Sem título"),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "author": entry.get("author", "Quanta Magazine"),
                    "published": entry.get("published", ""),
                    "image": image_url,
                }
            )
        return articles

    def _build_article_embed(self, article: dict, footer: str = "") -> discord.Embed:
        """Build a nice embed for a single article."""
        # Clean up summary (RSS often has HTML tags)
        summary = article["summary"]
        # Strip basic HTML tags
        for tag in ["<p>", "</p>", "<br>", "<br/>", "<br />"]:
            summary = summary.replace(tag, "")
        if len(summary) > 300:
            summary = summary[:297] + "..."

        embed = discord.Embed(
            title=article["title"],
            url=article["url"],
            description=summary,
            color=0xFF6600,  # Quanta orange
        )
        embed.set_author(
            name="Quanta Magazine",
            url="https://www.quantamagazine.org",
            icon_url="https://d2r55xnwy6nx47.cloudfront.net/uploads/2018/03/QM_Favicon-32x32.png",
        )
        if article["image"]:
            embed.set_image(url=article["image"])
        if article["author"]:
            embed.add_field(name="Autor", value=article["author"], inline=True)
        if article["published"]:
            embed.add_field(name="Publicado", value=article["published"], inline=True)
        if footer:
            embed.set_footer(text=footer)

        return embed

    # Daily auto-post

    @tasks.loop(time=DAILY_POST_TIME)
    async def daily_news(self):
        channel_id = self.config.get("channel_id")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        articles = self._fetch_articles(limit=1)
        if not articles:
            return

        article = articles[0]

        # Don't repost the same article
        if article["url"] == self.last_posted_url:
            return

        embed = self._build_article_embed(
            article, footer="📰 Notícia diária automática"
        )
        await channel.send(embed=embed)

        self.last_posted_url = article["url"]
        self.config["last_posted_url"] = article["url"]
        save_config(self.config)

    @daily_news.before_loop
    async def before_daily_news(self):
        await self.bot.wait_until_ready()

    # Commands

    @app_commands.command(
        name="news", description="Mostra os artigos mais recentes da Quanta Magazine"
    )
    @app_commands.describe(count="Número de artigos a mostrar (1–5)")
    async def news(self, interaction: discord.Interaction, count: int = 1):
        count = max(1, min(5, count))
        await interaction.response.defer()

        articles = self._fetch_articles(limit=count)
        if not articles:
            await interaction.followup.send(
                "Não consegui obter artigos de momento. Tenta mais tarde."
            )
            return

        for article in articles:
            embed = self._build_article_embed(article)
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="news-channel",
        description="Define o canal para notícias diárias automáticas",
    )
    @app_commands.describe(channel="O canal onde as notícias serão publicadas")
    @app_commands.default_permissions(administrator=True)
    async def set_news_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        self.config["channel_id"] = channel.id
        save_config(self.config)

        embed = discord.Embed(
            title="Canal de notícias configurado",
            description=f"As notícias diárias da Quanta Magazine serão publicadas em {channel.mention} todos os dias às 09:00 UTC.",
            color=0x57F287,  # Discord green
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="news-stop", description="Desativa as notícias diárias automáticas"
    )
    @app_commands.default_permissions(administrator=True)
    async def stop_news(self, interaction: discord.Interaction):
        self.config.pop("channel_id", None)
        save_config(self.config)

        embed = discord.Embed(
            title="Notícias diárias desativadas",
            description="As notícias automáticas foram desativadas. Usa `/news-channel` para reativar.",
            color=0xED4245,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="news-status", description="Mostra a configuração atual das notícias"
    )
    @app_commands.default_permissions(administrator=True)
    async def news_status(self, interaction: discord.Interaction):
        channel_id = self.config.get("channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            channel_text = (
                channel.mention if channel else f"ID desconhecido ({channel_id})"
            )
            status = f"Ativo, a publicar em {channel_text}"
        else:
            status = "Inativo, usa `/news-channel` para ativar"

        embed = discord.Embed(
            title="📰  Estado das Notícias",
            description=status,
            color=0x5865F2,
        )
        embed.add_field(name="Horário", value="Diariamente às 09:00 UTC", inline=True)
        embed.add_field(
            name="Fonte",
            value="[Quanta Magazine](https://www.quantamagazine.org)",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
