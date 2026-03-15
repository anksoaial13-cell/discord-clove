import os
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "https://clove-vinculo.onrender.com").rstrip("/")

from vinculacao.db import delete_link, init_db
from vinculacao.services import AppError, remove_rank_roles

TOKEN = os.getenv("TOKEN")

print("TOKEN LIDO?", TOKEN is not None)
print("VALOR TOKEN:", TOKEN)

# ICONS
ASSET_ICON = "assets/clove_icon.gif"

# IDS
TICKET_CATEGORY_ID = 1481744479072551142
SUPORTE_ROLE_ID = 1481754427848265811

# VIP ROLES
VIP_BASIC = 1482119405776273559
VIP_PRO = 1482119323987345569
VIP_PLUS = 1481754724658057368

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# LIMITES VIP
MAX_MEMBROS_BASIC = 5
MAX_MEMBROS_PRO = 15
MAX_MEMBROS_PLUS = 30

# inicializa banco da vinculação
init_db()

# --------------------------------
# SISTEMA DE TICKET
# --------------------------------

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red)
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Fechando o ticket...",
            ephemeral=True
        )
        await interaction.channel.delete()


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="dúvidas", description="tire suas dúvidas"),
            discord.SelectOption(label="denúncia", description="reporte um jogador"),
            discord.SelectOption(label="sugestão", description="envie uma sugestão"),
            discord.SelectOption(label="comprar VIP", description="adquirir VIP"),
            discord.SelectOption(label="outro assunto", description="outro tipo de suporte"),
        ]

        super().__init__(
            placeholder="selecione uma opção...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        categoria = guild.get_channel(TICKET_CATEGORY_ID)

        if categoria is None:
            await interaction.response.send_message(
                "A categoria de tickets não foi encontrada.",
                ephemeral=True
            )
            return

        # evitar ticket duplicado
        for canal in categoria.channels:
            if canal.name == f"ticket-{user.id}":
                await interaction.response.send_message(
                    f"Você já possui um ticket aberto: {canal.mention}",
                    ephemeral=True
                )
                return

        suporte_role = guild.get_role(SUPORTE_ROLE_ID)
        if suporte_role is None:
            await interaction.response.send_message(
                "O cargo de suporte não foi encontrado.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True),
            suporte_role: discord.PermissionOverwrite(view_channel=True)
        }

        tipo = self.values[0]

        canal = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            overwrites=overwrites,
            category=categoria
        )

        embed = discord.Embed(
            title="Ticket aberto",
            description=f"{user.mention} abriu um ticket de **{tipo}**.\nA staff irá te atender em breve.",
            color=0xB57EDC
        )

        await canal.send(
            content=f"{suporte_role.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"Seu ticket foi criado: {canal.mention}",
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@bot.command()
async def painel(ctx):
    embed = discord.Embed(
        title="<a:clove_kuromiwave:1464474803460247684> Central de Suporte da Clove",
        description=(
            "nesta seção, você pode abrir um ticket para tirar dúvidas, reportar problemas ou falar diretamente com a equipe da staff.\n\n"
            "para agilizar o atendimento, escolha a categoria correta e descreva seu problema com o máximo de detalhes possível."
        ),
        color=0xB57EDC
    )

    embed.set_image(
        url="https://win.gg/wp-content/uploads/2024/03/Valorant-agent-Clove.jpg.webp"
    )

    await ctx.send(embed=embed, view=TicketView())


# --------------------------------
# TICKET COMPRA VIP
# --------------------------------

class ComprarVIPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Comprar VIP",
        style=discord.ButtonStyle.green,
    )
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        categoria = guild.get_channel(TICKET_CATEGORY_ID)

        if categoria is None:
            await interaction.response.send_message(
                "A categoria de tickets não foi encontrada.",
                ephemeral=True
            )
            return

        # evitar ticket duplicado
        for canal in categoria.channels:
            if canal.name == f"vip-{user.id}":
                await interaction.response.send_message(
                    f"Você já possui um ticket aberto: {canal.mention}",
                    ephemeral=True
                )
                return

        suporte_role = guild.get_role(SUPORTE_ROLE_ID)
        if suporte_role is None:
            await interaction.response.send_message(
                "O cargo de suporte não foi encontrado.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            suporte_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        canal = await guild.create_text_channel(
            name=f"vip-{user.id}",
            overwrites=overwrites,
            category=categoria
        )

        embed = discord.Embed(
            title="Compra de VIP",
            description=(
                f"olá {user.mention}! seja bem-vindo ao **atendimento VIP da Clove**.\n\n"

                "**Planos disponíveis:**\n\n"

                "**VIP BASIC**\n"
                "• cargo personalizado\n"
                "• permissão para mudar seu apelido\n"
                "• até 5 membros\n\n"

                "**VIP PRO**\n"
                "• cargo personalizado\n"
                "• permissão para usar emojis externos\n"
                "• permissão para mudar seu apelido\n"
                "• até 15 membros\n\n"

                "**VIP PLUS**\n"
                "• cargo personalizado\n"
                "• permissão para usar emojis externos\n"
                "• permissão para mudar seu apelido\n"
                "• até 30 membros\n"
                "• prioridade em eventos\n\n"

                "Envie qual **plano deseja comprar** e a staff irá te atender."
            ),
            color=0xB57EDC
        )

        await canal.send(
            content=f"{user.mention} {suporte_role.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"Seu ticket foi criado: {canal.mention}",
            ephemeral=True
        )


@bot.command()
async def painel_vip(ctx):
    embed = discord.Embed(
        title="<a:clove_kuromiwave:1464474803460247684> SEJA VIP NA CLOVE",
        description=(
            "quer apoiar a **Clove** e desbloquear **benefícios exclusivos?**\n\n"

            "**VIP BASIC**\n"
            "• cargo personalizado\n"
            "• permissão para mudar seu apelido\n"
            "• até 5 membros\n\n"

            "**VIP PRO**\n"
            "• cargo personalizado\n"
            "• permissão para usar emojis externos\n"
            "• permissão para mudar seu apelido\n"
            "• até 15 membros\n\n"

            "**VIP PLUS**\n"
            "• cargo personalizado\n"
            "• permissão para usar emojis externos\n"
            "• permissão para mudar seu apelido\n"
            "• até 30 membros\n"
            "• prioridade em eventos\n\n"

            "clique no botão abaixo para **comprar seu VIP**."
        ),
        color=0xB57EDC
    )

    embed.set_image(
        url="https://i.pinimg.com/736x/75/94/a5/7594a5d19c876955139879762e3eb577.jpg"
    )

    await ctx.send(embed=embed, view=ComprarVIPView())


# --------------------------------
# SISTEMA VIP PERSONALIZADO
# --------------------------------

def get_vip_level(member):
    if discord.utils.get(member.roles, id=VIP_PLUS):
        return "plus"

    if discord.utils.get(member.roles, id=VIP_PRO):
        return "pro"

    if discord.utils.get(member.roles, id=VIP_BASIC):
        return "basic"

    return None


class CargoModal(discord.ui.Modal, title="Cargo VIP"):
    nome = discord.ui.TextInput(label="Nome do cargo")
    cor = discord.ui.TextInput(label="Cor HEX", placeholder="#ff66cc")
    membros = discord.ui.TextInput(label="IDs dos membros", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        role = discord.utils.get(guild.roles, name=f"vip-{user.id}")

        try:
            cor_hex = self.cor.value.replace("#", "")
            cor = discord.Color(int(cor_hex, 16))
        except ValueError:
            await interaction.response.send_message(
                "Cor HEX inválida. Exemplo: #ff66cc",
                ephemeral=True
            )
            return

        if role is None:
            role = await guild.create_role(
                name=f"vip-{user.id}",
                colour=cor
            )
            await user.add_roles(role)

        await role.edit(
            name=self.nome.value,
            colour=cor
        )

        await interaction.response.send_message(
            "Cargo atualizado!",
            ephemeral=True
        )


class CargoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar / Editar Cargo", style=discord.ButtonStyle.blurple)
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CargoModal())


@bot.command()
async def painel_cargo(ctx):
    if not get_vip_level(ctx.author):
        await ctx.send("Apenas VIP pode usar.")
        return

    embed = discord.Embed(
        title="Cargos VIP Personalizados",
        description="Crie ou edite seu cargo VIP.",
        color=0xB57EDC
    )

    await ctx.send(embed=embed, view=CargoView())


def get_vip_type(member):
    if discord.utils.get(member.roles, id=VIP_PLUS):
        return "PLUS", 30

    if discord.utils.get(member.roles, id=VIP_PRO):
        return "PRO", 15

    if discord.utils.get(member.roles, id=VIP_BASIC):
        return "BASIC", 5

    return None, 0


class PainelVIP(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar Cargo Personalizado", style=discord.ButtonStyle.primary)
    async def criar_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        vip, limite = get_vip_type(interaction.user)

        if not vip:
            await interaction.response.send_message("Você não possui VIP.", ephemeral=True)
            return

        guild = interaction.guild

        role = await guild.create_role(
            name=f"VIP | {interaction.user.name}",
            colour=discord.Colour.random()
        )

        await interaction.user.add_roles(role)

        await interaction.response.send_message(
            f"Cargo **{role.name}** criado com sucesso!",
            ephemeral=True
        )

    @discord.ui.button(label="Alterar Apelido", style=discord.ButtonStyle.secondary)
    async def apelido(self, interaction: discord.Interaction, button: discord.ui.Button):
        vip, limite = get_vip_type(interaction.user)

        if not vip:
            await interaction.response.send_message("Você não possui VIP.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Envie no chat o **novo apelido** que deseja.",
            ephemeral=True
        )

    @discord.ui.button(label="Adicionar Membros", style=discord.ButtonStyle.success)
    async def membros(self, interaction: discord.Interaction, button: discord.ui.Button):
        vip, limite = get_vip_type(interaction.user)

        if not vip:
            await interaction.response.send_message("Você não possui VIP.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Você pode adicionar até **{limite} membros** ao seu VIP.\n"
            "Envie as **menções dos membros**.",
            ephemeral=True
        )

    @discord.ui.button(label="Ativar Emojis Externos", style=discord.ButtonStyle.secondary)
    async def emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        vip, limite = get_vip_type(interaction.user)

        if vip not in ["PRO", "PLUS"]:
            await interaction.response.send_message(
                "Apenas **VIP PRO ou PLUS** possuem esse benefício.",
                ephemeral=True
            )
            return

        await interaction.user.edit(nick=interaction.user.display_name)

        await interaction.response.send_message(
            "Permissão para usar **emojis externos** ativada!",
            ephemeral=True
        )

    @discord.ui.button(label="Prioridade em Eventos", style=discord.ButtonStyle.danger)
    async def eventos(self, interaction: discord.Interaction, button: discord.ui.Button):
        vip, limite = get_vip_type(interaction.user)

        if vip != "PLUS":
            await interaction.response.send_message(
                "Apenas **VIP PLUS** possui prioridade em eventos.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Você possui **prioridade em eventos**!",
            ephemeral=True
        )


@bot.command()
async def vip(ctx):
    embed = discord.Embed(
        title="Painel VIP",
        description="""
Bem-vindo ao **Painel VIP**!

Use os botões abaixo para gerenciar seus benefícios.

VIP BASIC
• cargo personalizado
• mudar apelido
• até 5 membros

VIP PRO
• cargo personalizado
• emojis externos
• mudar apelido
• até 15 membros

VIP PLUS
• cargo personalizado
• emojis externos
• mudar apelido
• até 30 membros
• prioridade em eventos
""",
        color=0x8a2be2
    )

    await ctx.send(embed=embed, view=PainelVIP())


# --------------------------------
# SISTEMA DE VINCULAÇÃO VALORANT
# --------------------------------

class LinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        # 1º botão: vincular
        self.add_item(
            discord.ui.Button(
                label="vincular conta",
                style=discord.ButtonStyle.link,
                url=f"{BASE_URL}/login",
                emoji="🔗"
            )
        )

        # 2º botão: resetar
        reset_button = discord.ui.Button(
            label="resetar",
            style=discord.ButtonStyle.danger,
            custom_id="reset_link_button"
        )
        reset_button.callback = self.reset_callback
        self.add_item(reset_button)

    async def reset_callback(self, interaction: discord.Interaction):
        try:
            remove_rank_roles(str(interaction.user.id))
            delete_link(str(interaction.user.id))

            await interaction.response.send_message(
                "✅ sua vinculação foi resetada com sucesso.",
                ephemeral=True
            )
        except AppError as exc:
            await interaction.response.send_message(
                f"❌ {exc}",
                ephemeral=True
            )


@bot.command()
async def painel_vinculo(ctx):
    embed = discord.Embed(
        title="Verificação",
        description=(
            "para manter a comunidade organizada e segura, conecte sua conta Valorant ao servidor.\n\n"
            "certifique-se de que sua conta Riot está vinculada ao seu Discord antes de iniciar."
        ),
        color=0xB57EDC
    )

    embed.add_field(
        name="aviso",
        value=(
            "```"
            "esta integração é feita entre você e o\n"
            "próprio Discord, e não teremos acesso nenhum\n"
            "à sua conta."
            "```"
        ),
        inline=False
    )

    embed.set_footer(text="Clique em Vincular conta para começar.")

    file = discord.File("assets/clove.gif", filename="clove.gif")
    embed.set_thumbnail(url="attachment://clove.gif")

    await ctx.send(embed=embed, view=LinkView(), file=file)


@bot.command()
async def resetar_vinculo(ctx):
    try:
        remove_rank_roles(str(ctx.author.id))
        delete_link(str(ctx.author.id))
        await ctx.send("✅ sua vinculação foi removida e seus cargos de elo foram resetados.")
    except AppError as exc:
        await ctx.send(f"❌ {exc}")


@bot.tree.command(name="painel_vinculo_slash", description="envia o painel de vinculação do Valorant")
@app_commands.checks.has_permissions(administrator=True)
async def painel_vinculo_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Verificação",
        description=(
            "afim de manter uma comunidade limpa e saudável, solicitamos que você "
            "conecte sua conta Valorant ao servidor.\n\n"
            "Antes de fazer isso, é necessário vincular sua conta Riot à sua conta do Discord."
        ),
        color=0xB57EDC
    )

    embed.add_field(
        name="Aviso",
        value=(
            "```"
            "Esta integração é feita entre você e o\n"
            "próprio Discord, e não teremos acesso nenhum\n"
            "à sua conta."
            "```"
        ),
        inline=False
    )

    embed.set_footer(text="Clique em Vincular conta para começar.")

    if os.path.exists(ASSET_ICON):
        file = discord.File(ASSET_ICON, filename="clove_icon.gif")
        embed.set_thumbnail(url="attachment://clove_icon.gif")
        await interaction.response.send_message(embed=embed, view=LinkView(), file=file)
    else:
        await interaction.response.send_message(embed=embed, view=LinkView())


@bot.tree.command(name="resetar_vinculo_slash", description="Remove a vinculação e os cargos de elo")
async def resetar_vinculo_slash(interaction: discord.Interaction):
    try:
        remove_rank_roles(str(interaction.user.id))
        delete_link(str(interaction.user.id))
        await interaction.response.send_message(
            "✅ Sua vinculação foi removida e seus cargos de elo foram resetados.",
            ephemeral=True
        )
    except AppError as exc:
        await interaction.response.send_message(
            f"❌ {exc}",
            ephemeral=True
        )



@bot.event
async def on_ready():   
    try:
        synced = await bot.tree.sync()
        print(f"Bot conectado como {bot.user} | Slash commands sincronizados: {len(synced)}")
    except Exception as exc:
        print(f"Falha ao sincronizar slash commands: {exc}")

    print("Bot está pronto!")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Defina TOKEN no arquivo .env")
    bot.run(TOKEN)
