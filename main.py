import os
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
import urllib.request
import json
import asyncio
import re

TOKEN = os.environ.get("DISCORD_TOKEN")

# הגדרת הבוט לעבודה עם פקודות רגילות מבוססות סימן קריאה (!)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🎯 כתובת ה-IP הישירה של שרת ה-FiveM שלכם וקובץ הרקע שהעלית
SERVER_IP = "188.66.26.143"
SERVER_PORT = "30120"
BACKGROUND_IMAGE = "background.png"

# מזהי רשת ומערכת קבועים ומדויקים של שרת GamePlay IL
GUILD_ID = 1500997764169863271

# רולים משטרתיים
ROLE_APPROVER_ID = 1521553580148916325 # רול אישור דרגות
STAFF_TICKET_ROLE_ID = 1521554756626157788 # רול צוות הטיקטים
SAY_COMMAND_ROLE_ID = 1521602302622961857 # הרול הבלעדי שיכול להשתמש בפקודות ההכרזה

# חדרים רשמיים בשרת
WELCOME_CHANNEL_ID = 1500997767256870922
ROLE_PANEL_CHANNEL_ID = 1521623331990933544 # 🎯 חדר פנל ההכרזות הראשי (say-פנל) מהקישור שלך
ROLE_APPROVAL_LOG_CHANNEL_ID = 1521554909021868073
TICKET_PANEL_CHANNEL_ID = 1521555870268260423
TICKET_LOG_CHANNEL_ID = 1521557178387795999
ROLE_GIVEN_LOG_CHANNEL_ID = 1521575503448768683 
SERVER_AUDIT_LOG_CHANNEL_ID = 1521596321721487491 # חדר לוגי אבטחה אוטומטיים

# משתנה גלובלי לשמירת מצב הלולאה (0 = שחקנים, 1 = סטטוס אונליין/אופליין)
status_cycle = 0

# ==========================================
# 🌐 שרת אינטרנט פנימי למניעת קריסה (Keep Alive)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Police Bot GamePlay IL is Running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)
# ==========================================
# 👋 מערכת ברוכים הבאים ועזיבה (WELCOME & LEAVE SYSTEM)
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != GUILD_ID: return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return

    embed = discord.Embed(
        title="✨ חבר חדש הצטרף למחלקת המשטרה!",
        description=(
            f"ברוך הבא {member.mention} אל השרת הרשמי של **GamePlay IL**!\n\n"
            f"➔ אתה החבר ה-**{len(member.guild.members)}** בקהילה.\n"
            f"➔ אנา היכנס לערוץ האימות או פתח פנייה לקבלת דרגות שירות."
        ),
        color=0x1a73e8
    )
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        
    if member.avatar: embed.set_thumbnail(url=member.avatar.url)
    else: embed.set_thumbnail(url=member.default_avatar.url)
    embed.set_footer(text="Developed by Aharon the gamer")

    if os.path.exists(BACKGROUND_IMAGE):
        await channel.send(file=file, embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")
    else:
        await channel.send(embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")

@bot.event
async def on_member_remove(member: discord.Member):
    if member.guild.id != GUILD_ID: return
    log_channel = member.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log_channel: return

    embed = discord.Embed(
        title="🏃‍♂️ משתמש עזב את השרת",
        description=f"המשתמש **{member.name}** ({member.mention}) עזב את שרת המשטרה ברגע זה.\n\n**מזהה משתמש:** `{member.id}`",
        color=discord.Color.red()
    )
    if member.avatar: embed.set_thumbnail(url=member.avatar.url)
    else: embed.set_thumbnail(url=member.default_avatar.url)
    embed.set_footer(text="Developed by Aharon the gamer")
    
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        await log_channel.send(file=file, embed=embed)
    else:
        await log_channel.send(embed=embed)
# ==========================================
# 🎖️ מערכת פנל רולים ואישורים (ROLE REQUEST SYSTEM)
# ==========================================
class RoleRequestModal(discord.ui.Modal, title="טופס הגשת בקשת רולים - GamePlay IL"):
    staff_name = discord.ui.TextInput(label="שם השוטר / חבר הצוות שהכניס אותך", placeholder="לדוגמה: אהרון", required=True)
    role_reason = discord.ui.TextInput(label="פירוט הרולים או הדרגות שאתה אמור לקבל", placeholder="לדוגמה: שוטר סיור", style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        log_channel = guild.get_channel(ROLE_APPROVAL_LOG_CHANNEL_ID)
        if not log_channel: return

        embed = discord.Embed(
            title="📥 בקשת רולים חדשה ממתינה לאישור",
            description=f"**מגיש הבקשה:** {interaction.user.mention} (`{interaction.user.id}`)\n**הגורם המאשר:** `{self.staff_name.value}`\n\n**פירוט הרולים המבוקשים:**\n```{self.role_reason.value}```",
            color=0xffa500
        )
        if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
        embed.set_footer(text="Developed by Aharon the gamer")

        view = RoleApprovalView(interaction.user.id)
        options = [discord.SelectOption(label=role.name, value=str(role.id), emoji="👮‍♂️") for role in sorted(guild.roles, reverse=True) if not role.is_default() and not role.managed][:25]
        for item in view.children:
            if isinstance(item, DynamicRoleSelect): item.options = options
        
        if os.path.exists(BACKGROUND_IMAGE):
            file = discord.File(BACKGROUND_IMAGE, filename="background.png")
            await log_channel.send(file=file, embed=embed, view=view)
        else:
            await log_channel.send(embed=embed, view=view)
        await interaction.followup.send("✅ הטופס נשלח בהצלחה לחדר אישורי ההנהלה!", ephemeral=True)
class DynamicRoleSelect(discord.ui.Select):
    def __init__(self, target_user_id: int):
        self.target_user_id = target_user_id
        super().__init__(placeholder="בחר רולים להענקה ולנעילת הפנייה...", min_values=1, max_values=15, custom_id="dynamic_role_selector_spec")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target: return

        added_roles = []
        for role_id_str in self.values:
            role = guild.get_role(int(role_id_str))
            if role:
                try:
                    await target.add_roles(role)
                    added_roles.append(role.name)
                except discord.Forbidden: pass

        if not added_roles:
            return await interaction.followup.send("❌ שגיאה: לא ניתן להעניק את הרולים.", ephemeral=True)

        roles_list = ", ".join(added_roles)

        try:
            dm_embed = discord.Embed(title="🚨 עדכון מחלקת המשטרה | בקשתך אושרה! ✨", description=f"שלום {target.mention},\nטופס בקשת הדרגות שלך אושר!\n\n**🎖️ הדרגות/רולים שקיבלת:**\n```{roles_list}```", color=discord.Color.green())
            await target.send(embed=dm_embed)
        except: pass

        locked_embed = discord.Embed(title="🔒 פניית בקשת רולים טופלה וננעלה", color=discord.Color.green())
        if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
        locked_embed.add_field(name="🛡️ סטטוס מערכת", value="✅ הרולים הוענקו והפנל ננעל.", inline=False)
        locked_embed.add_field(name="👮‍♂️ מנהל מטפל", value=interaction.user.mention, inline=True)
        locked_embed.add_field(name="👤 המשתמש שקיבל", value=target.mention, inline=True)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        await interaction.message.edit(embed=locked_embed, view=None)

        log_channel = guild.get_channel(ROLE_GIVEN_LOG_CHANNEL_ID)
        if log_channel:
            given_embed = discord.Embed(title="🎖️ לוג רשמי - הענקת דרגות", description=f"**המנהל המאשר:** {interaction.user.mention}\n**המשתמש שקיבל:** {target.mention}\n\n**הרולים שהוענקו:**\n```{roles_list}```", color=0x1a73e8)
            if os.path.exists(BACKGROUND_IMAGE):
                given_embed.set_image(url="attachment://background.png")
                await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=given_embed)
            else:
                await log_channel.send(embed=given_embed)

        await interaction.followup.send(f"🎖️ הדרגות הוענקו בהצלחה והודעת DM נשלחה!", ephemeral=True)
class RoleApprovalView(discord.ui.View):
    def __init__(self, target_user_id: int):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.add_item(DynamicRoleSelect(target_user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if ROLE_APPROVER_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ אין לך את ההרשאות הדרושות לביצוע פעולות בפנל זה.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ענישה: BAN", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="admin_action_ban_spec")
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = interaction.guild.get_member(self.target_user_id)
        if target:
            try: await target.send("נדחת וקיבלת באן ממערכות השרת.")
            except: pass
            await target.ban(reason="נדחה בטופס הדרגות.")
            
        locked_embed = discord.Embed(title="🔒 פניית בקשת רולים נדחתה וננעלה", color=discord.Color.red())
        if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
        locked_embed.add_field(name="🛡️ סטטוס מערכת", value="❌ המשתמש נדחה, נחסם מהשרת (BAN) ופנל השליטה הושבת.", inline=False)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        await interaction.message.edit(embed=locked_embed, view=None)
        await interaction.response.send_message("🔨 המשתמש נחסם והפנל ננעל.", ephemeral=True)

    @discord.ui.button(label="ענישה: KICK", style=discord.ButtonStyle.secondary, emoji="🚪", custom_id="admin_action_kick_spec")
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = interaction.guild.get_member(self.target_user_id)
        if target:
            try: await target.send("נדחת ונזרקת מהשרת.")
            except: pass
            await target.kick(reason="נדחה בטופס הדרגות.")
            
        locked_embed = discord.Embed(title="🔒 פניית בקשת רולים נדחתה וננעלה", color=discord.Color.orange())
        if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
        locked_embed.add_field(name="🛡️ סטטוס מערכת", value="🚪 המשתמש נדחה, נזרק מהשרת (KICK) ופנל השליטה הושבת.", inline=False)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        await interaction.message.edit(embed=locked_embed, view=None)
        await interaction.response.send_message("🚪 המשתמש נזרק והפנל ננעל.", ephemeral=True)

    @discord.ui.button(label="סיום פנייה ונתינת רולים", style=discord.ButtonStyle.success, emoji="✅", custom_id="admin_action_finish_spec")
    async def finish_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        locked_embed = discord.Embed(title="🔒 פניית בקשת רולים נסגרה ידנית", color=discord.Color.green())
        if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
        locked_embed.add_field(name="🛡️ סטטוס פנייה", value=f"✅ נסגר ידנית על ידי {interaction.user.mention}!", inline=False)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        await interaction.message.edit(embed=locked_embed, view=None)
        await interaction.response.send_message("✅ הפנייה נסגרה ידנית!", ephemeral=True)
        self.stop()

class RoleRequestStarterView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="להגשת בקשת רולים ודרגות", style=discord.ButtonStyle.primary, emoji="🎖️", custom_id="start_role_req_btn_spec")
    async def start_request(self, interaction: discord.Interaction, button: discord.ui.Button): await interaction.response.send_modal(RoleRequestModal())
class TicketActionButtons(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self.claimed_by = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if STAFF_TICKET_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ ההרשאה חסומה לחברי צוות הטיקטים בלבד.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="לקיחת הפנייה", style=discord.ButtonStyle.success, emoji="📌", custom_id="ticket_claim_spec")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed_by:
            return await interaction.response.send_message(f"❌ טיקט זה כבר נלקח לטיפול על ידי {self.claimed_by.mention}.", ephemeral=True)
        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"בטיפול של: {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"📌 הטיקט בטיפול של {interaction.user.mention}!")

    @discord.ui.button(label="שינוי שם חדר", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="ticket_rename_spec")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        class RenameModal(discord.ui.Modal, title="שינוי שם חדר הטיקט"):
            new_name = discord.ui.TextInput(label="השם החדש", placeholder="בטיפול", required=True)
            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                await inter.channel.edit(name=self.new_name.value)
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="הוספת משתמש", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_user_spec")
    async def add_user_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 אנא תייג או רשום מזהה ID של האדם שברצונך להוסיף לחדר ברגע זה בצ'אט:", ephemeral=True)
        def check(m): return m.channel.id == interaction.channel.id and m.author.id == interaction.user.id
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            target = None
            if msg.mentions: target = msg.mentions
            else:
                m = re.search(r'\d+', msg.content)
                if m: target = interaction.guild.get_member(int(m.group()))
            if target:
                await interaction.channel.set_permissions(target, view_channel=True, send_messages=True)
                await interaction.channel.send(f"✅ המשתמש {target.mention} נוסף לטיקט!")
        except: pass

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_main_spec")
    async def close_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 החדר יימחק בעוד 3 שניות...")
        await asyncio.sleep(3)
        await interaction.channel.delete()
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="שאלה כללית", emoji="❓", value="שאלה כללית"),
            discord.SelectOption(label="דיווח באג", emoji="🐛", value="דיווח באג"),
            discord.SelectOption(label="תלונה על שוטר", emoji="🚨", value="תלונה על שוטר")
        ]
        super().__init__(placeholder="בחר את סוג הפנייה שלך מתוך הרשימה...", min_values=1, max_values=1, options=options, custom_id="ticket_dropdown_select_main_spec")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        ticket_type = self.values[0] # שולף איבר ראשון מהרשימה בצורה מדויקת
        
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        staff_role = guild.get_role(STAFF_TICKET_ROLE_ID)
        if staff_role: overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"{ticket_type}-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title=f"🎫 פנייה חדשה בנושא: {ticket_type}", description="צוות הטיקטים יהיה איתך בהקדם.", color=0x2f3136)
        embed.set_footer(text="Developed by Aharon the gamer")

        await channel.send(embed=embed, view=TicketActionButtons(interaction.user.id))
        await interaction.response.send_message(f"✅ הטיקט שלך נפתח בהצלחה בערוץ: {channel.mention}", ephemeral=True)

class TicketStarterView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(TicketDropdown())

@bot.command(name="setup_role_panel")
@commands.has_permissions(administrator=True)
async def setup_role_panel_cmd(ctx):
    guild = ctx.guild
    channel = guild.get_channel(ROLE_PANEL_CHANNEL_ID)
    if not channel: return await ctx.send("❌ חדר פנל הרולים לא נמצא.")
    
    embed = discord.Embed(title="🎖️ מחלקת משטרת GamePlay-IL | בקשת דרגות ורולים", description="לחצו על הכפתור למטה ומלאו את הפרטים במדויק.", color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
    
    view = RoleRequestStarterView()
    if os.path.exists(BACKGROUND_IMAGE):
        await channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except Exception: pass

@bot.command(name="setup_ticket_panel")
@commands.has_permissions(administrator=True)
async def setup_ticket_panel_cmd(ctx):
    await ctx.send(embed=discord.Embed(title="🎫 מחלקת המשטרה | פתיחת פניות ותמיכה"), view=TicketStarterView())
    try: await ctx.message.delete()
    except: pass
class SayChannelDropdown(discord.ui.Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=ch.name, value=str(ch.id), emoji="📢") for ch in channels[:25]]
        super().__init__(placeholder="בחר את ערוץ היעד להצבת ההכרזה...", options=options, custom_id="say_panel_dropdown_selector")

    async def callback(self, interaction: discord.Interaction):
        has_role = any(role.id == SAY_COMMAND_ROLE_ID for role in interaction.user.roles)
        if not has_role:
            return await interaction.response.send_message("❌ ההרשאה חסומה לבעלי תפקיד הכרזות בלבד.", ephemeral=True)

        guild = interaction.guild
        target_channel = guild.get_channel(int(self.values[0]))
        if not target_channel:
            return await interaction.response.send_message("❌ ערוץ היעד לא נמצא.", ephemeral=True)

        await interaction.response.send_message(f"👮‍♂️ אנא הקלד כעת (בהודעה הבאה שלך בצ'אט) את המלל הרשמי שברצונך לשגר לחדר {target_channel.mention}:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            user_msg = await bot.wait_for('message', check=check, timeout=60.0)
            try: await user_msg.delete()
            except: pass

            embed = discord.Embed(description=user_msg.content, color=0x1a73e8)
            embed.set_footer(text="Developed by Aharon the gamer")

            if os.path.exists(BACKGROUND_IMAGE):
                embed.set_image(url="attachment://background.png")
                await target_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
            else:
                await target_channel.send(embed=embed)

            await interaction.followup.send(f"✅ ההכרזה שוגרה בהצלחה לערוץ {target_channel.mention}!", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ עבר הזמן המוקצב (60 שניות). הפעולה בבוטלה.", ephemeral=True)

class SayPanelStarterView(discord.ui.View):
    def __init__(self, channels=None):
        super().__init__(timeout=None)
        if channels: self.add_item(SayChannelDropdown(channels))

@bot.command(name="setup_say_panel")
@commands.has_permissions(administrator=True)
async def setup_say_panel_cmd(ctx):
    text_channels = [ch for ch in ctx.guild.channels if isinstance(ch, discord.TextChannel)]
    embed = discord.Embed(
        title="📢 מחלקת משטרת GamePlay-IL | מערכת שיגור הכרזות",
        description="בחר מתוך התפריט הנפתח למטה את חדר היעד שאליו תרצה לשלוח הודעה רשמית בשם הבוט.",
        color=0x1a73e8
    )
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")

    view = SayPanelStarterView(text_channels)
    if os.path.exists(BACKGROUND_IMAGE):
        await ctx.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except: pass

# ==========================================
# 📊 משימה אוטומטית ברקע - פנייה ישירה ל-FiveM (מתחלף כל 10 שניות במדויק!)
# ==========================================
@tasks.loop(seconds=10)
async def track_fivem_status():
    global status_cycle
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    players_count, max_players, server_online = 0, 8, False
    try:
        url_players = f"http://{SERVER_IP}:{SERVER_PORT}/players.json"
        req_players = urllib.request.Request(url_players)
        req_players.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req_players, timeout=4) as response:
            players_count = len(json.loads(response.read().decode()))
            server_online = True
    except Exception: server_online = False
        
    try:
        url_info = f"http://{SERVER_IP}:{SERVER_PORT}/info.json"
        req_info = urllib.request.Request(url_info)
        req_info.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req_info, timeout=4) as info_response:
            info_data = json.loads(info_response.read().decode())
            max_players = int(info_data.get('Data', {}).get('sv_maxclients', info_data.get('sv_maxclients', 8)))
    except Exception: pass
        
    if status_cycle == 0:
        status_text = f"{players_count}/{max_players} שחקנים" if server_online else f"0/{max_players}"
        status_cycle = 1
    else:
        status_text = "Online 🟢" if server_online else "Offline 🔴"
        status_cycle = 0
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_text))

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if channel.guild.id != GUILD_ID: return
    log = channel.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if log: await log.send(embed=discord.Embed(title="📁 חדר נוצר", description=f"החדר {channel.mention} נוצר בשרת.", color=discord.Color.green()))

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    if channel.guild.id != GUILD_ID: return
    log = channel.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if log: await log.send(embed=discord.Embed(title="🗑️ חדר נמחק", description=f"החדר `{channel.name}` נמחק מהשרת.", color=discord.Color.red()))
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    
    guild = bot.get_guild(GUILD_ID)
    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
    
    bot.add_view(RoleRequestStarterView())
    bot.add_view(TicketStarterView())
    bot.add_view(SayPanelStarterView(text_channels)) 
    if not track_fivem_status.is_running(): track_fivem_status.start()

# הפעלת מנוע הבוט 24/7
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    if TOKEN: bot.run(TOKEN)
