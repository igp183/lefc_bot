import discord
from discord import app_commands
from discord.ext import commands

ASSIGNABLE_ROLES = [
    "1º Ano",
    "2º Ano",
    "3º Ano",
    "Infiltrado",
    "Licenciatura",
    "Mestrado",
    "Doutoramento",
    "LEFC",
]


class RoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=role, value=role) for role in ASSIGNABLE_ROLES
        ]
        super().__init__(
            placeholder="Escolhe o role que queres...",
            min_values=0,
            max_values=len(options),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = set(self.values)
        member = interaction.user
        guild = interaction.guild

        added = []
        removed = []

        for role_name in ASSIGNABLE_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role is None:
                continue

            if role_name in selected and role not in member.roles:
                await member.add_roles(role)
                added.append(role_name)
            elif role_name not in selected and role in member.roles:
                await member.remove_roles(role)
                removed.append(role_name)

        parts = []
        if added:
            parts.append(f"**Added:** {', '.join(added)}")
        if removed:
            parts.append(f"**Removed:** {', '.join(removed)}")
        if not parts:
            parts.append("No changes made")

        await interaction.response.send_message("\n".join(parts), ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roles", description="Escolhe o role que queres...")
    async def roles(self, interaction: discord.Interaction):
        view = RoleView()
        await interaction.response.send_message(
            "Escolhe os roles:", view=view, ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))
