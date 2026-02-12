import discord
from discord import app_commands
from discord.ext import commands

EMBED_COLOR = 0x5865F2  # Discord blurple
DEFAULT_COG_EMOJI = "📦"


def get_cog_emoji(cog: commands.Cog) -> str:
    """Gets an emoji from a cog. Define `emoji = '...'` within the cog to customize."""
    return getattr(cog, "emoji", DEFAULT_COG_EMOJI)


class HelpSelect(discord.ui.Select):
    """Dropdown that lets you choose a cog and see its commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = []

        for cog_name, cog in bot.cogs.items():
            description = cog.description or "Sem descrição"
            if len(description) > 100:
                description = description[:97] + "..."

            options.append(
                discord.SelectOption(
                    label=cog_name,
                    description=description,
                    emoji=get_cog_emoji(cog),
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

        emoji = get_cog_emoji(cog)

        embed = discord.Embed(
            title=f"{emoji}  {cog_name}",
            description=cog.description or "Sem descrição.",
            color=EMBED_COLOR,
        )

        # Slash commands
        slash_cmds = cog.get_app_commands()
        if slash_cmds:
            lines = []
            for cmd in slash_cmds:
                params = " ".join(f"`<{p.name}>`" for p in cmd.parameters)
                desc = f" — {cmd.description}" if cmd.description else ""
                lines.append(f"`/{cmd.name}` {params}{desc}")
            embed.add_field(
                name="Comandos Slash",
                value="\n".join(lines),
                inline=False,
            )

        # Prefix commands
        prefix_cmds = [c for c in cog.get_commands() if not c.hidden]
        if prefix_cmds:
            lines = []
            for cmd in prefix_cmds:
                sig = f" {cmd.signature}" if cmd.signature else ""
                desc = f" — {cmd.short_doc}" if cmd.short_doc else ""
                lines.append(f"`!{cmd.name}{sig}`{desc}")
            embed.add_field(
                name="Comandos com Prefixo",
                value="\n".join(lines),
                inline=False,
            )

        if not slash_cmds and not prefix_cmds:
            embed.add_field(
                name="Comandos",
                value="Este módulo não tem comandos (apenas aguarda por eventos).",
                inline=False,
            )

        embed.set_footer(text="Usa o dropdown para explorar outros módulos.")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(bot))
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass


class Help(commands.Cog):
    """Shows all the commands available on the bot."""

    emoji = "❓"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.remove_command("help")

    @app_commands.command(name="help", description="Vê todos os comandos disponíveis")
    async def help_slash(self, interaction: discord.Interaction):
        embed = self._build_overview()
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        """Vê todos os comandos disponíveis."""
        embed = self._build_overview()
        view = HelpView(self.bot)
        view.message = await ctx.send(embed=embed, view=view)

    def _build_overview(self) -> discord.Embed:
        embed = discord.Embed(
            title="📖  Comandos do Bot",
            description=(
                "Aqui tens uma visão geral de todos os comandos disponíveis.\n"
                "Usa o dropdown abaixo para explorar cada módulo em detalhe."
            ),
            color=EMBED_COLOR,
        )

        for cog_name, cog in self.bot.cogs.items():
            emoji = get_cog_emoji(cog)

            cmd_names = []
            for cmd in cog.get_app_commands():
                cmd_names.append(f"`/{cmd.name}`")
            for cmd in cog.get_commands():
                if not cmd.hidden:
                    cmd_names.append(f"`!{cmd.name}`")

            if cmd_names:
                embed.add_field(
                    name=f"{emoji}  {cog_name}",
                    value=" · ".join(cmd_names),
                    inline=False,
                )

        embed.set_footer(text="Seleciona um módulo abaixo para ver mais detalhes.")
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
