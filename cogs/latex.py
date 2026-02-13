import urllib.parse

import discord
from discord import app_commands
from discord.ext import commands


class Latex(commands.Cog):
    """Renders LaTeX expressions as an image."""

    emoji = "📐"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="latex", description="Renderiza uma expressão LaTeX")
    @app_commands.describe(expression="A expressão LaTeX (ex: E = mc^2)")
    async def latex_slash(self, interaction: discord.Interaction, expression: str):
        embed = self._build_embed(expression)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="latex")
    async def latex_prefix(self, ctx: commands.Context, *, expression: str):
        """Renderiza uma expressão LaTeX. Ex: !latex E = mc^2"""
        embed = self._build_embed(expression)
        await ctx.send(embed=embed)

    def _build_embed(self, expression: str) -> discord.Embed:
        # White text on transparent background, 300 DPI
        encoded = urllib.parse.quote(expression)
        url = (
            f"https://latex.codecogs.com/png.image?"
            f"\\dpi{{300}}\\color{{white}}{encoded}"
        )

        embed = discord.Embed(color=0x5865F2)
        embed.set_image(url=url)
        embed.set_footer(text=expression)
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(Latex(bot))
