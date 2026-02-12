import discord
from discord import app_commands
from discord.ext import commands

RESOURCES = {
    "Geral": {
        "Moodle": "https://moodle.uma.pt/",
        "Infoalunos": "https://infoalunos.uma.pt/",
    },
    "Física": {
        "Física Experimental": "https://jglg.uma.pt/Ens/Fexp/index.php",
        "Ciências Experimentais": "https://jglg.uma.pt/Ens/Cexp/index.php",
    },
    "Programming": {
        "Python Docs": "https://docs.python.org/3/",
        "Real Python": "https://realpython.com/",
    },
    "Matemática": {
        "3Blue1Brown": "https://www.3blue1brown.com/",
        "Wolfram Alpha": "https://www.wolframalpha.com/",
    },
}


class Resources(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="resources", description="Mostra links importantes para o curso"
    )
    @app_commands.describe(category="Filtra por categoria (opcional)")
    @app_commands.choices(
        category=[app_commands.Choice(name=cat, value=cat) for cat in RESOURCES.keys()]
    )
    async def resources(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] = None,
    ):
        embed = discord.Embed(title="Course Resources", color=discord.Color.green())

        cats = {category.value: RESOURCES[category.value]} if category else RESOURCES

        for cat_name, links in cats.items():
            link_list = "\n".join(f"[{name}]({url})" for name, url in links.items())
            embed.add_field(name=cat_name, value=link_list, inline=False)

        embed.set_footer(text="Queres adicionar algum link? Contribui no GitHub!")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Resources(bot))
