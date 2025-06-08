import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# ✅ โหลด .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ ชื่อ Role สำหรับ verify
ROLE_NAME = "𝘃𝗲𝗿𝗶𝗳𝘆"

# ✅ Category ID สำหรับ Ticket
TICKET_CATEGORY_ID = 1381274625765544016

# =================== ระบบ Verify ปุ่ม ===================
class RoleButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ กดรับยศ", style=discord.ButtonStyle.green, emoji="🎖️")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
        if not role:
            await interaction.response.send_message("❌ Role ไม่พบใน server!", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("😎 คุณมียศนี้อยู่แล้ว!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ คุณได้รับยศ **{ROLE_NAME}** เรียบร้อย!", ephemeral=True)

@bot.command(name="postembed")
@commands.has_permissions(administrator=True)
async def post_embed(ctx):
    embed = discord.Embed(
        title="🪄 รับยศ 𝘃𝗲𝗿𝗶𝗳𝘆",
        description="กดปุ่มข้างล่างเพื่อรับยศ **𝘃𝗲𝗿𝗶𝗳𝘆** ได้เลย!",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1161030439857131550.gif?size=96&quality=lossless")
    embed.set_footer(text="🎨 ระบบแจกยศ by Xeno")

    view = RoleButtonView()
    await ctx.send(embed=embed, view=view)

@post_embed.error
async def post_embed_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (เฉพาะแอดมินเท่านั้น!)")

# =================== ระบบ Ticket Panel ===================
class TicketView(discord.ui.View):
    def __init__(self, creator: discord.Member):
        super().__init__(timeout=None)
        self.creator = creator
        self.embed_msg = None
        self.updater_task = None

    @discord.ui.button(label="❌ ปิด Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.creator and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ปิด Ticket!", ephemeral=True)
            return

        await interaction.response.send_message("✅ ปิด Ticket เรียบร้อย!", ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()

    async def start_updater(self, message: discord.Message):
        self.embed_msg = message
        self.updater_task = asyncio.create_task(self.update_embed())

    async def update_embed(self):
        while True:
            embed = self.embed_msg.embeds[0]
            embed.set_field_at(0, name="🕰️ อัพเดตล่าสุด", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
            await self.embed_msg.edit(embed=embed)
            await asyncio.sleep(10)

class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ สร้าง Ticket", style=discord.ButtonStyle.green, emoji="📝")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ ไม่พบ Category ที่กำหนด! แจ้งแอดมินตรวจสอบ ID", ephemeral=True)
            return

        for channel in category.channels:
            if channel.topic == f"Ticket ของ {interaction.user.id}":
                await interaction.response.send_message("❌ คุณสร้าง Ticket ไว้แล้ว! ปิดของเดิมก่อนนะ", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for member in guild.members:
            if member.guild_permissions.administrator and member.status != discord.Status.offline:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{interaction.user.name.lower()}"
        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, topic=f"Ticket ของ {interaction.user.id}")

        embed = discord.Embed(
            title="🎟️ Ticket ",
            description=f"👤 โดย: {interaction.user.mention}\n✅ Ticket สร้างเรียบร้อย!",
            color=discord.Color.green()
        )
        embed.add_field(name="🕰️ อัพเดตล่าสุด", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.set_footer(text="🦾 Ticket System by Xeno")

        view = TicketView(interaction.user)
        ticket_msg = await ticket_channel.send(embed=embed, view=view)
        await view.start_updater(ticket_msg)

        await interaction.response.send_message(f"✅ Ticket ของคุณอยู่ที่: {ticket_channel.mention}", ephemeral=True)

        for member in guild.members:
            if member.guild_permissions.administrator and member.status != discord.Status.offline:
                try:
                    await member.send(f"📬 Ticket ใหม่จาก {interaction.user} ➜ {ticket_channel.mention}")
                except:
                    pass

@bot.command(name="ticketpanel")
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    embed = discord.Embed(
        title="🎫 ระบบ Ticket เท่ๆ",
        description="กดปุ่มข้างล่างเพื่อสร้าง Ticket ได้เลย!",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1161030439857131550.gif?size=96&quality=lossless")
    embed.add_field(name="🕰️ อัพเดตล่าสุด", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.set_footer(text="🦾 Ticket System by Xeno")

    view = CreateTicketView()
    await ctx.send(embed=embed, view=view)

@ticket_panel.error
async def ticket_panel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (เฉพาะแอดมินเท่านั้น!)")

@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")

bot.run(TOKEN)
