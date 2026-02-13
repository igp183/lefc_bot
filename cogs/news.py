"""
News Cog — Automated and on-demand science news from RSS feeds.

Features:
    - Daily auto-post to an admin-configured channel
    - On-demand /news and !news commands
    - Multiple feed support (add more in FEEDS)
    - Admin commands to configure channel and active feed
    - Deduplication to avoid reposting

Configuration is stored in data/news_config.json and persists across restarts.
"""

import json
import re
from datetime import time
from pathlib import Path
from typing import Callable, Coroutine, Optional

import discord
import feedparser
from discord import app_commands
from discord.ext import commands, tasks

# Feed Registry, add new feeds here and they just work

FEEDS: dict[str, dict] = {
    "quanta": {
        "name": "Quanta Magazine",
        "url": "https://api.quantamagazine.org/feed/",
        "icon": "https://d2r55xnwy6nx47.cloudfront.net/uploads/2018/03/QM_Favicon-32x32.png",
        "home": "https://www.quantamagazine.org",
        "color": 0xFF6600,
    },
    "arxiv-physics": {
        "name": "arXiv — Physics",
        "url": "https://rss.arxiv.org/rss/physics",
        "icon": "https://info.arxiv.org/brand/images/brand-logomark-primary.jpg",
        "home": "https://arxiv.org/list/physics/new",
        "color": 0xB31B1B,
    },
    "phys-org": {
        "name": "Phys.org",
        "url": "https://phys.org/rss-feed/",
        "icon": "https://phys.org/favicon.ico",
        "home": "https://phys.org",
        "color": 0x1A1A2E,
    },
}

DEFAULT_FEED = "quanta"

# Settings

CONFIG_DIR = Path("data")
CONFIG_FILE = CONFIG_DIR / "news_config.json"
DAILY_POST_TIME = time(hour=9, minute=0)  # 09:00 UTC
MAX_SUMMARY_LENGTH = 300
MAX_ARTICLES = 5

# Config persistence


class NewsConfig:
    """Thin wrapper around a JSON file for news settings."""

    __slots__ = ("_path", "_data")

    DEFAULTS = {
        "channel_id": None,
        "feed": DEFAULT_FEED,
        "last_posted_url": None,
    }

    def __init__(self, path: Path = CONFIG_FILE):
        self._path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path, "r") as f:
                stored = json.load(f)
            return {**self.DEFAULTS, **stored}
        return {**self.DEFAULTS}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def __getitem__(self, key: str):
        return self._data[key]

    def __setitem__(self, key: str, value):
        self._data[key] = value
        self.save()

    def __delitem__(self, key: str):
        self._data[key] = self.DEFAULTS.get(key)
        self.save()

    @property
    def active_feed(self) -> dict:
        return FEEDS.get(self._data["feed"], FEEDS[DEFAULT_FEED])


# Article model


class Article:
    """Parsed article from an RSS entry."""

    __slots__ = ("title", "url", "summary", "author", "published", "image")

    def __init__(self, entry: feedparser.FeedParserDict):
        self.title: str = entry.get("title", "Sem título")
        self.url: str = entry.get("link", "")
        self.summary: str = self._clean_html(entry.get("summary", ""))
        self.author: str = entry.get("author", "")
        self.published: str = entry.get("published", "")
        self.image: Optional[str] = self._extract_image(entry)

    @staticmethod
    def _clean_html(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = text.strip()
        if len(text) > MAX_SUMMARY_LENGTH:
            text = text[: MAX_SUMMARY_LENGTH - 3] + "..."
        return text

    @staticmethod
    def _extract_image(entry: feedparser.FeedParserDict) -> Optional[str]:
        for attr in ("media_content", "media_thumbnail"):
            media_list = getattr(entry, attr, None)
            if media_list:
                for media in media_list:
                    url = media.get("url")
                    if url:
                        return url
        return None

    def to_embed(self, feed: dict, footer: str = "") -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            url=self.url,
            description=self.summary,
            color=feed["color"],
        )
        embed.set_author(
            name=feed["name"],
            url=feed["home"],
            icon_url=feed["icon"],
        )
        if self.image:
            embed.set_image(url=self.image)
        if self.author:
            embed.add_field(name="Autor", value=self.author, inline=True)
        if self.published:
            embed.add_field(name="Publicado", value=self.published, inline=True)
        if footer:
            embed.set_footer(text=footer)
        return embed


# Type alias for any send-like callable
SendFunc = Callable[..., Coroutine]


class News(commands.Cog):
    """Notícias diárias de ciência e matemática a partir de feeds RSS."""

    emoji = "📰"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = NewsConfig()

    async def cog_load(self):
        self.daily_news.start()

    async def cog_unload(self):
        self.daily_news.cancel()

    # Feed helpers

    @staticmethod
    def fetch_articles(feed_url: str, limit: int = 5) -> list[Article]:
        feed = feedparser.parse(feed_url)
        return [Article(entry) for entry in feed.entries[:limit]]

    # Shared command logic

    async def _cmd_news(self, send: SendFunc, count: int = 1):
        count = max(1, min(MAX_ARTICLES, count))
        feed = self.config.active_feed
        articles = self.fetch_articles(feed["url"], limit=count)

        if not articles:
            await send("Não consegui obter artigos de momento. Tenta mais tarde.")
            return

        for article in articles:
            await send(embed=article.to_embed(feed))

    async def _cmd_set_channel(self, send: SendFunc, channel: discord.TextChannel):
        self.config["channel_id"] = channel.id
        feed = self.config.active_feed
        embed = discord.Embed(
            title="Canal de notícias configurado",
            description=(
                f"As notícias diárias de **{feed['name']}** serão publicadas "
                f"em {channel.mention} todos os dias às 09:00 UTC."
            ),
            color=0x57F287,
        )
        await send(embed=embed)

    async def _cmd_stop(self, send: SendFunc):
        del self.config["channel_id"]
        embed = discord.Embed(
            title="Notícias diárias desativadas",
            description="Usa `/news-channel` para reativar.",
            color=0xED4245,
        )
        await send(embed=embed)

    async def _cmd_set_feed(self, send: SendFunc, feed_key: str):
        if feed_key not in FEEDS:
            available = ", ".join(f"`{k}`" for k in FEEDS)
            await send(f"Feed desconhecido. Feeds disponíveis: {available}")
            return

        self.config["feed"] = feed_key
        feed = FEEDS[feed_key]
        embed = discord.Embed(
            title="Feed atualizado",
            description=f"O feed ativo é agora **{feed['name']}**.",
            color=feed["color"],
        )
        await send(embed=embed)

    async def _cmd_status(self, send: SendFunc):
        channel_id = self.config["channel_id"]
        feed = self.config.active_feed

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            where = channel.mention if channel else f"ID desconhecido ({channel_id})"
            status = f"Ativo, a publicar em {where}"
        else:
            status = "Inativo, usa `/news-channel` para ativar"

        embed = discord.Embed(
            title="📰  Estado das Notícias",
            description=status,
            color=0x5865F2,
        )
        embed.add_field(
            name="Feed", value=f"[{feed['name']}]({feed['home']})", inline=True
        )
        embed.add_field(name="Horário", value="Diariamente às 09:00 UTC", inline=True)

        available = ", ".join(f"`{k}`" for k in FEEDS)
        embed.add_field(name="Feeds disponíveis", value=available, inline=False)

        await send(embed=embed)

    async def _cmd_feeds(self, send: SendFunc):
        active_key = self.config["feed"]
        embed = discord.Embed(
            title="📰  Feeds Disponíveis",
            description="Usa `/news-feed <nome>` para mudar o feed ativo.",
            color=0x5865F2,
        )
        for key, feed in FEEDS.items():
            marker = "  ← ativo" if key == active_key else ""
            embed.add_field(
                name=f"{feed['name']}{marker}",
                value=f"`{key}` · [Website]({feed['home']})",
                inline=False,
            )
        await send(embed=embed)

    # Slash commands

    @app_commands.command(name="news", description="Mostra os artigos mais recentes")
    @app_commands.describe(count="Número de artigos a mostrar (1–5)")
    async def news_slash(self, interaction: discord.Interaction, count: int = 1):
        await interaction.response.defer()
        await self._cmd_news(interaction.followup.send, count)

    @app_commands.command(
        name="news-channel", description="Define o canal para notícias diárias"
    )
    @app_commands.describe(channel="O canal onde as notícias serão publicadas")
    @app_commands.default_permissions(administrator=True)
    async def set_channel_slash(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await self._cmd_set_channel(interaction.response.send_message, channel)

    @app_commands.command(name="news-stop", description="Desativa as notícias diárias")
    @app_commands.default_permissions(administrator=True)
    async def stop_slash(self, interaction: discord.Interaction):
        await self._cmd_stop(interaction.response.send_message)

    @app_commands.command(name="news-feed", description="Muda o feed RSS ativo")
    @app_commands.describe(feed="Nome do feed")
    @app_commands.choices(
        feed=[
            app_commands.Choice(name=info["name"], value=key)
            for key, info in FEEDS.items()
        ]
    )
    @app_commands.default_permissions(administrator=True)
    async def set_feed_slash(
        self, interaction: discord.Interaction, feed: app_commands.Choice[str]
    ):
        await self._cmd_set_feed(interaction.response.send_message, feed.value)

    @app_commands.command(
        name="news-status", description="Mostra a configuração atual das notícias"
    )
    @app_commands.default_permissions(administrator=True)
    async def status_slash(self, interaction: discord.Interaction):
        await self._cmd_status(interaction.response.send_message)

    @app_commands.command(name="feeds", description="Lista todos os feeds disponíveis")
    async def feeds_slash(self, interaction: discord.Interaction):
        await self._cmd_feeds(interaction.response.send_message)

    # Prefix commands

    @commands.command(name="news")
    async def news_prefix(self, ctx: commands.Context, count: int = 1):
        """Mostra os artigos mais recentes."""
        await self._cmd_news(ctx.send, count)

    @commands.command(name="news-channel")
    @commands.has_permissions(administrator=True)
    async def set_channel_prefix(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Define o canal para notícias diárias."""
        await self._cmd_set_channel(ctx.send, channel)

    @commands.command(name="news-stop")
    @commands.has_permissions(administrator=True)
    async def stop_prefix(self, ctx: commands.Context):
        """Desativa as notícias diárias."""
        await self._cmd_stop(ctx.send)

    @commands.command(name="news-feed")
    @commands.has_permissions(administrator=True)
    async def set_feed_prefix(self, ctx: commands.Context, feed: str):
        """Muda o feed RSS ativo."""
        await self._cmd_set_feed(ctx.send, feed)

    @commands.command(name="news-status")
    @commands.has_permissions(administrator=True)
    async def status_prefix(self, ctx: commands.Context):
        """Mostra a configuração atual das notícias."""
        await self._cmd_status(ctx.send)

    @commands.command(name="feeds")
    async def feeds_prefix(self, ctx: commands.Context):
        """Lista todos os feeds disponíveis."""
        await self._cmd_feeds(ctx.send)

    # Daily auto-post

    @tasks.loop(time=DAILY_POST_TIME)
    async def daily_news(self):
        channel_id = self.config["channel_id"]
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        feed = self.config.active_feed
        articles = self.fetch_articles(feed["url"], limit=1)
        if not articles:
            return

        article = articles[0]
        if article.url == self.config["last_posted_url"]:
            return

        await channel.send(
            embed=article.to_embed(feed, footer="📰 Notícia diária automática")
        )
        self.config["last_posted_url"] = article.url

    @daily_news.before_loop
    async def before_daily_news(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
