import discord
from discord import app_commands
from discord.ext import commands


class HelpSelect(discord.ui.Select):
    """Dropdown menu that lets users pick a cog to see its commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = []
        for cog_name, cog in bot.cogs.items():
            if cog_name == "Help":
                continue  # don't list ourselves
            description = cog.description or "Sem descrição"
            # Truncate to 100 chars which is the discord limit for select descriptions
            if len(description) > 100:
                description = description[:97] + "..."
            options.append(
                discord.SelectOption(
                    label=cog_name,
                    description=description,
                    emoji=getattr(cog, "emoji", None),
                )
            )

        if not options:
            options.append(
                discord.SelectOption(label="Nenhum módulo carregado", value="none")
            )

        super().__init__(
            placeholder="Escolhe um módulo para ver os seus comandos...",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        cog = self.bot.get_cog(cog_name)
        if cog is None:
            await interaction.response.send_message(
                "Esse módulo já não existe.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"{cog_name}",
            description=cog.description or "Sem descrição.",
            color=discord.Color.blue(),
        )

        # Slash commands
        slash_cmds = cog.get_app_commands()
        if slash_cmds:
            lines = []
            for cmd in slash_cmds:
                params = " ".join(f"`<{p.name}>`" for p in cmd.parameters)
                line = f"**/{cmd.name}** {params}"
                if cmd.description:
                    line += f"\n  {cmd.description}"
                lines.append(line)
            embed.add_field(
                name="Comandos de barra",
                value="\n".join(lines),
                inline=False,
            )

        # Prefix commands
        prefix_cmds = [c for c in cog.get_commands() if not c.hidden]
        if prefix_cmds:
            lines = []
            for cmd in prefix_cmds:
                sig = cmd.signature or ""
                line = f"**!{cmd.name}** {sig}"
                if cmd.short_doc:
                    line += f"\n  {cmd.short_doc}"
                lines.append(line)
            embed.add_field(
                name="Comandos de prefixo",
                value="\n".join(lines),
                inline=False,
            )

        if not slash_cmds and not prefix_cmds:
            embed.add_field(
                name="Comandos",
                value="Este módulo não tem comandos (pode simplesmente reagir a eventos).",
                inline=False,
            )

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    """Shows an overview of all available commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Remove the default help command so ours doesn't conflict
        self.bot.remove_command("help")

    @app_commands.command(
        name="help", description="Verifica todos os comandos disponíveis"
    )
    async def help_slash(self, interaction: discord.Interaction):
        embed = self._build_overview()
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        """See all available commands."""
        embed = self._build_overview()
        view = HelpView(self.bot)
        await ctx.send(embed=embed, view=view)

    def _build_overview(self) -> discord.Embed:
        embed = discord.Embed(
            title="Comandos do bot",
            description=(
                "Usa o dropwdown a baixo para explorar os módulos, "
                "de qualquer forma aqui estão todos os comandos."
            ),
            color=discord.Color.blue(),
        )

        for cog_name, cog in self.bot.cogs.items():
            if cog_name == "Help":
                continue

            cmd_names = []
            for cmd in cog.get_app_commands():
                cmd_names.append(f"`/{cmd.name}`")
            for cmd in cog.get_commands():
                if not cmd.hidden:
                    cmd_names.append(f"`!{cmd.name}`")

            if cmd_names:
                embed.add_field(
                    name=cog_name,
                    value=" ".join(cmd_names),
                    inline=False,
                )

        embed.set_footer(text="Seleciona um módulo para ver mais detalhes.")
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
