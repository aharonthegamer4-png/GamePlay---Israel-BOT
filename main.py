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

# מזהי החדרים הרשמיים והמדויקים של השרת
WELCOME_CHANNEL_ID = 1500997767256870922
FIVEM_STATUS_CHANNEL_ID = 1500997767256870925 # חדר סטטוס שחקנים בלייב המעודכן שלך!
SAY_PANEL_CHANNEL_ID = 1521623331990933544     # חדר פנל סיי (say-פנל)
ROLE_PANEL_CHANNEL_ID = 1500997767256870923    # חדר פנל בקשת רולים
TICKET_PANEL_CHANNEL_ID = 1521555870268260423  # חדר פנל פתיחת טיקטים

# חדרים פנימיים ללוגים, אבטחה ותיעוד פקודות
ROLE_APPROVAL_LOG_CHANNEL_ID = 1521554909021868073
TICKET_LOG_CHANNEL_ID = 1521557178387795999    # לוגי טיקטים (סגירת פניות)
SERVER_AUDIT_LOG_CHANNEL_ID = 1521596321721487491 # לוגי מערכת כלליים (אבטחה וחדרים)
ROLE_GIVEN_LOG_CHANNEL_ID = 1521575503448768683 
COMMAND_LOG_CHANNEL_ID = 1521847015019909180   # חדר תיעוד פקודות (Command Logger)

# משתנה גלובלי לשמירת מזהה הודעת הסטטוס הקבועה כדי לערוך אותה בלייב
status_message_id = None

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
            f"➔ אנא היכנס לערוץ האימות או פתח פנייה לקבלת דרגות שירות."
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
        await interaction.response.send_message("👤 אנא תייג את הבנאדם או רשום מזהה ID שלו בצ'אט כעת:", ephemeral=True)
        def check(m): return m.channel.id == interaction.channel.id and m.author.id == interaction.user.id
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            target = None
            if msg.mentions: 
                target = msg.mentions
            else:
                m = re.search(r'\d+', msg.content)
                if m: target = interaction.guild.get_member(int(m.group()))
                
            if target:
                await interaction.channel.set_permissions(target, view_channel=True, send_messages=True, attach_files=True)
                await interaction.channel.send(f"✅ המשתמש {target.mention} נוסף בהצלחה לטיקט על ידי {interaction.user.mention}!")
                try: await msg.delete()
                except: pass
            else:
                await interaction.channel.send("❌ שגיאה: לא זוהה משתמש תקין בשרת. הפעולה בבוטלה.")
        except asyncio.TimeoutError:
            await interaction.channel.send("❌ עבר הזמן המוקצב להוספת משתמש. אנא לחץ שוב.")

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_main_spec")
    async def close_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TicketCloseModal(discord.ui.Modal, title="סיכום וסגירת טיקט"):
            summary = discord.ui.TextInput(label="פירוט תמציתי של מה שהיה בטיקט", style=discord.TextStyle.long, required=True)
            answered = discord.ui.TextInput(label="האם הטיקט קיבל מענה מלא? (כן / לא)", required=True)
            def __init__(self, creator_id_val: int): super().__init__(); self.creator_id_val = creator_id_val

            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=False)
                guild = inter.guild
                
                log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
                creator = guild.get_member(self.creator_id_val)

                log_embed = discord.Embed(title="🔒 פניית טיקט נסגרה ותועדה במערכת", color=discord.Color.red())
                log_embed.add_field(name="חדר הטיקט המקורי", value=f"`{inter.channel.name}`", inline=True)
                log_embed.add_field(name="נסגר על ידי המנהל", value=inter.user.mention, inline=True)
                log_embed.add_field(name="פתח את הטיקט", value=creator.mention if creator else f"`{self.creator_id_val}`", inline=True)
                log_embed.add_field(name="האם קיבל מענה?", value=self.answered.value, inline=True)
                log_embed.add_field(name="סיכום ותמצית הטיפול", value=f"```{self.summary.value}```", inline=False)
                log_embed.set_footer(text="Developed by Aharon the gamer")
                if os.path.exists(BACKGROUND_IMAGE): log_embed.set_image(url="attachment://background.png")

                if log_channel:
                    if os.path.exists(BACKGROUND_IMAGE): await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=log_embed)
                    else: await log_channel.send(embed=log_embed)
                await asyncio.sleep(3)
                await inter.channel.delete()

        await interaction.response.send_modal(TicketCloseModal(self.creator_id))
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
        ticket_type = self.values
        
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

@bot.command(name="setup_say_panel")
@commands.has_permissions(administrator=True)
async def setup_say_panel_cmd(ctx):
    target_channel = ctx.guild.get_channel(SAY_PANEL_CHANNEL_ID)
    if not target_channel: return
    text_channels = [ch for ch in ctx.guild.channels if isinstance(ch, discord.TextChannel)]
    embed = discord.Embed(title="📢 מחלקת משטרת GamePlay-IL | מערכת שיגור הכרזות", description="בחר מתוך התפריט הנפתח למטה את חדר היעד.", color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
    view = SayPanelStarterView(text_channels)
    if os.path.exists(BACKGROUND_IMAGE): await target_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else: await target_channel.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except: pass

@bot.command(name="setup_role_panel")
@commands.has_permissions(administrator=True)
async def setup_role_panel_cmd(ctx):
    target_channel = ctx.guild.get_channel(ROLE_PANEL_CHANNEL_ID)
    if not target_channel: return
    embed = discord.Embed(title="🎖️ מחלקת משטרת GamePlay-IL | בקשת דרגות ורולים", description="לחצו על הכפתור למטה ומלאו את ...", color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
    view = RoleRequestStarterView()
    if os.path.exists(BACKGROUND_IMAGE): await target_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else: await target_channel.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except: pass

@bot.command(name="setup_ticket_panel")
@commands.has_permissions(administrator=True)
async def setup_ticket_panel_cmd(ctx):
    target_channel = ctx.guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not target_channel: return
    embed = discord.Embed(title="🎫 מחלקת המשטרה | פתיחת פניות ותמיכה", description="בחרו את קטגוריית הפנייה המתאימה מתוך התפריט.", color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
    view = TicketStarterView()
    if os.path.exists(BACKGROUND_IMAGE): await target_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else: await target_channel.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except: pass
class SayChannelDropdown(discord.ui.Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=ch.name, value=str(ch.id), emoji="📢") for ch in channels[:25]]
        super().__init__(placeholder="בחר את ערוץ היעד להצבת ההכרזה...", options=options, custom_id="say_panel_dropdown_selector")

    async def callback(self, interaction: discord.Interaction):
        has_role = any(role.id == SAY_COMMAND_ROLE_ID for role in interaction.user.roles)
        if not has_role: return await interaction.response.send_message("❌ חסום.", ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(int(self.values))
        if not target_channel: return
        await interaction.response.send_message(f"👮‍♂️ אנא הקלד כעת את המלל באפיק השיחה:", ephemeral=True)
        def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        try:
            user_msg = await bot.wait_for('message', check=check, timeout=60.0)
            try: await user_msg.delete()
            except: pass
            embed = discord.Embed(description=user_msg.content, color=0x1a73e8)
            embed.set_footer(text="Developed by Aharon the gamer")
            if os.path.exists(BACKGROUND_IMAGE):
                embed.set_image(url="attachment://background.png")
                await target_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
            else: await target_channel.send(embed=embed)
        except asyncio.TimeoutError: pass

class SayPanelStarterView(discord.ui.View):
    def __init__(self, channels=None):
        super().__init__(timeout=None)
        if channels: self.add_item(SayChannelDropdown(channels))

@bot.command(name="say", aliases=["SAY", "Say"])
async def say_command(ctx, *, message: str = None):
    has_role = any(role.id == SAY_COMMAND_ROLE_ID for role in ctx.author.roles)
    if not has_role: return
    if not message: return
    try: await ctx.message.delete()
    except: pass
    embed = discord.Embed(description=message, color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
        await ctx.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
    else: await ctx.send(embed=embed)

# ==========================================
# 📊 מערכת לוגי מערכת אוטומטיים משוכללת (Audit Logs Tracker)
# ==========================================
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if channel.guild.id != GUILD_ID: return
    log = channel.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log: return
    
    responsible_staff = "לא זוהה מנהל"
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            responsible_staff = entry.user.mention
            break
    except: pass

    embed = discord.Embed(title="📁 חדר נוצר בשרת", description=f"**שם החדר:** {channel.mention}\n**נוצר על ידי:** {responsible_staff}", color=discord.Color.green())
    embed.set_footer(text="Developed by Aharon the gamer")
    try: await log.send(embed=embed)
    except: pass

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    if channel.guild.id != GUILD_ID: return
    log = channel.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log: return
    
    responsible_staff = "לא זוהה מנהל"
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            responsible_staff = entry.user.name
            break
    except: pass

    embed = discord.Embed(title="🗑️ חדר נמחק מהשרת", description=f"**שם החדר:** `{channel.name}`\n**נמחק על ידי:** {responsible_staff}", color=discord.Color.red())
    embed.set_footer(text="Developed by Aharon the gamer")
    try: await log.send(embed=embed)
    except: pass

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.guild.id != GUILD_ID: return
    log = before.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log: return

    # לוג הענקת רול
    if len(before.roles) < len(after.roles):
        new_role = next(role for role in after.roles if role not in before.roles)
        responsible_staff = "מערכת דיסקורד / בוט"
        try:
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    responsible_staff = entry.user.mention
                    break
        except: pass

        embed = discord.Embed(title="🟢 רול הוענק למשתמש בשרת", description=f"**המשתמש שקיבל:** {after.mention}\n**הרול שהוענק:** {new_role.mention}\n**הוענק על ידי:** {responsible_staff}", color=discord.Color.green())
        embed.set_footer(text="Developed by Aharon the gamer")
        try: await log.send(embed=embed)
        except: pass

    # לוג הסרת רול
    elif len(before.roles) > len(after.roles):
        removed_role = next(role for role in before.roles if role not in after.roles)
        responsible_staff = "מערכת דיסקורד / בוט"
        try:
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    responsible_staff = entry.user.mention
                    break
        except: pass

        embed = discord.Embed(title="🔴 רול הוסר ממשתמש בשרת", description=f"**המשתמש:** {after.mention}\n**הרול שהוסר:** {removed_role.mention}\n**הוסר על ידי:** {responsible_staff}", color=discord.Color.red())
        embed.set_footer(text="Developed by Aharon the gamer")
        try: await log.send(embed=embed)
        except: pass

@bot.event
async def on_guild_role_create(role: discord.Role):
    if role.guild.id != GUILD_ID: return
    log = role.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log: return
    responsible_staff = "לא זוהה"
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            responsible_staff = entry.user.mention
            break
    except: pass
    embed = discord.Embed(title="✨ רול חדש נוצר בשרת", description=f"**שם הרול:** {role.mention}\n**נוצר על ידי:** {responsible_staff}", color=discord.Color.blue())
    embed.set_footer(text="Developed by Aharon the gamer")
    await log.send(embed=embed)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    if role.guild.id != GUILD_ID: return
    log = role.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log: return
    responsible_staff = "לא זוהה"
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            responsible_staff = entry.user.name
            break
    except: pass
    embed = discord.Embed(title="🗑️ רול נמחק מהשרת", description=f"**שם הרול שנמחק:** `{role.name}`\n**נמחק על ידי:** {responsible_staff}", color=discord.Color.dark_red())
    embed.set_footer(text="Developed by Aharon the gamer")
    await log.send(embed=embed)

# 🎯 📝 מערכת תיעוד הפקודות הרשמית (Command Logger)!
@bot.event
async def on_command(ctx):
    log_chan = ctx.guild.get_channel(COMMAND_LOG_CHANNEL_ID)
    if not log_chan: return
    embed = discord.Embed(title="🚨 פקודת בוט הורצה בשרת", description=f"**חבר הצוות:** {ctx.author.mention} (`{ctx.author.id}`)\n**הפקודה שהורצה:** `{ctx.message.content}`\n**באפיק השיחה:** {ctx.channel.mention}", color=0x1a73e8)
    embed.set_footer(text="Command Logger System")
    await log_chan.send(embed=embed)
class QuickConnectButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        url = f"fivem://connect/{SERVER_IP}:{SERVER_PORT}"
        self.add_item(discord.ui.Button(label="כניסה מהירה לשרת 🚓", url=url, style=discord.ButtonStyle.link))

@tasks.loop(seconds=10)
async def track_fivem_status():
    global status_cycle, status_message_id
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    
    status_channel = guild.get_channel(FIVEM_STATUS_CHANNEL_ID)
    if not status_channel: return

    players_count, max_players, server_online = 0, 64, False
    players_list = []
    
    # 🎯 שלב 1: משיכת נתוני השחקנים והסלוטים בלייב בצורה חסינה
    try:
        url_players = f"http://{SERVER_IP}:{SERVER_PORT}/players.json"
        req_players = urllib.request.Request(url_players, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_players, timeout=3) as response:
            data = json.loads(response.read().decode())
            players_count = len(data)
            server_online = True
            for p in data:
                players_list.append(f"• `{p.get('name', 'Unknown')}` (ID: {p.get('id', '0')})")
    except:
        try:
            url_players = f"http://{SERVER_IP}/players.json"
            req_players = urllib.request.Request(url_players, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_players, timeout=3) as response:
                data = json.loads(response.read().decode())
                players_count = len(data)
                server_online = True
                for p in data:
                    players_list.append(f"• `{p.get('name', 'Unknown')}` (ID: {p.get('id', '0')})")
        except: server_online = False

    # 🎯 שלב 2: 🆕 קריאה אוטומטית ודינמית של כמות הסלוטים המקסימלית (info.json) של השרת שלכם!
    if server_online:
        try:
            url_info = f"http://{SERVER_IP}:{SERVER_PORT}/info.json"
            req_info = urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_info, timeout=3) as info_response:
                info_data = json.loads(info_response.read().decode())
                max_players = int(info_data.get('Data', {}).get('sv_maxclients', info_data.get('sv_maxclients', 64)))
        except:
            try:
                url_info = f"http://{SERVER_IP}/info.json"
                req_info = urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_info, timeout=3) as info_response:
                    info_data = json.loads(info_response.read().decode())
                    max_players = int(info_data.get('Data', {}).get('sv_maxclients', info_data.get('sv_maxclients', 64)))
            except: max_players = 64

    status_title = "GamePlay-IL | Israeli RolePlay"
    embed = discord.Embed(title=status_title, color=0x1a73e8)
    embed.add_field(name="📑 מערכת רשימת שחקנים", value="​", inline=False)
    embed.add_field(name="🔹 מצב השרת:", value="🟢 ONLINE" if server_online else "🔴 OFFLINE", inline=True)
    embed.add_field(name="👥 כמות שחקנים:", value=f"{players_count}/{max_players}", inline=True)
    
    percentage = int((players_count / max_players) * 100) if server_online and max_players > 0 else 0
    embed.add_field(name="⭐ מקום:", value=f"{percentage}%", inline=True)
    embed.add_field(name="🌐 חיבור לשרת:", value=f"Connect {SERVER_IP}", inline=False)
    
    joined_players = "\n".join(players_list) if players_list else "אין שחקנים מחוברים"
    if len(joined_players) > 1024: joined_players = joined_players[:1000] + "\n...ועוד שחקנים"
    
    embed.add_field(name="📡 שחקנים מחוברים", value=joined_players, inline=False)
    embed.set_footer(text="Developed by Aharon the gamer") # חתימה באנגלית
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")

    if status_message_id is None:
        async for msg in status_channel.history(limit=20):
            if msg.author.id == bot.user.id and msg.embeds and msg.embeds.title == status_title:
                status_message_id = msg.id
                break
                
    if status_message_id:
        try:
            msg = await status_channel.fetch_message(status_message_id)
            await msg.edit(embed=embed, view=QuickConnectButton())
        except:
            if os.path.exists(BACKGROUND_IMAGE):
                new_msg = await status_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=QuickConnectButton())
            else: new_msg = await status_channel.send(embed=embed, view=QuickConnectButton())
            status_message_id = new_msg.id
    else:
        if os.path.exists(BACKGROUND_IMAGE):
            new_msg = await status_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=QuickConnectButton())
        else: new_msg = await status_channel.send(embed=embed, view=QuickConnectButton())
        status_message_id = new_msg.id

    if status_cycle == 0:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{players_count}/{max_players} שחקנים" if server_online else f"0/{max_players}"))
        status_cycle = 1
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Online 🟢" if server_online else "Offline 🔴"))
        status_cycle = 0

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    guild = bot.get_guild(GUILD_ID)
    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
    bot.add_view(RoleRequestStarterView())
    bot.add_view(TicketStarterView())
    bot.add_view(SayPanelStarterView(text_channels)) 
    if not track_fivem_status.is_running(): track_fivem_status.start()

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    if TOKEN: bot.run(TOKEN)
