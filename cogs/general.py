import discord
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("  Ready")

    # command !ping
    @commands.command()
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! `{latency}ms`")

    # command /ping
    @app_commands.command(name="ping", description="Verifica o ping do bot")
    async def slash_ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency}ms`")

    # command /about
    @app_commands.command(name="about", description="Sobre o bot")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="lidl bot",
            description=(
                "**Contribuições:** [GitHub](https://github.com/igp183/lefc_bot)\n"
                "**Prefixos:** `!` ou usa `/comandos` com barra"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Licenciatura em Engenharia Física e Computacional")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
