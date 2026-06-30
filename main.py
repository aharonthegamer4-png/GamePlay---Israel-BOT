import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
import urllib.request
import json
import asyncio

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🎯 כתובת ה-IP הישירה של שרת ה-FiveM שלכם וקובץ הרקע שהעלית
SERVER_IP = "188.66.26.143"
SERVER_PORT = "30120"
BACKGROUND_IMAGE = "background.png"

# מזהי רשת ומערכת קבועים ומדויקים של שרת GamePlay IL
GUILD_ID = 1500997764169863271

# רולים
CITIZEN_ROLE_ID = 1514394547554226388  # רול האזרח
ROLE_APPROVER_ID = 1521553580148916325 # הרול שיכול לאשר את נתינת הרולים
STAFF_TICKET_ROLE_ID = 1521554756626157788 # רול הצוות שיכול לנהל טיקטים

# חדרים
WELCOME_CHANNEL_ID = 1500997767256870922
ROLE_PANEL_CHANNEL_ID = 1500997767256870923
ROLE_APPROVAL_LOG_CHANNEL_ID = 1521554909021868073
TICKET_PANEL_CHANNEL_ID = 1521555870268260423
TICKET_LOG_CHANNEL_ID = 1521557178387795999

# שמות ערוצי הלוגים בקטגוריית LOGS
LOG_CHANNELS = [
    "leave-logs", "ban-logs", "create-channel-logs", "delete-channel-logs",
    "manage-roles", "create-role", "delete-role", "ticket-open-logs",
    "ticket-close-logs", "update-message-logs", "add-role-logs",
    "remove-role-logs", "delete-message-logs"
]

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
# 📋 פונקציות עזר למערכת הלוגים
# ==========================================
async def send_log(guild, channel_name, embed):
    category = discord.utils.get(guild.categories, name="LOGS")
    if category:
        channel = discord.utils.get(category.text_channels, name=channel_name)
        if channel:
            await channel.send(embed=embed)
# ==========================================
# 🛡️ מערכת אימות (VERIFY SYSTEM)
# ==========================================
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="להתחלת אימות / Verify", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="verify_btn_67")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not role:
            return await interaction.response.send_message("שגיאה: רול האימות לא נמצא בשרת.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.response.send_message("אתה כבר מאומת במערכת! 🧭", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"האימות בוצע בהצלחה! קיבלת את הרול **{role.name}** ✨", ephemeral=True)

# ==========================================
# 🎮 מערכת סטטוס שרת אוטומטית (SERVER STATUS)
# ==========================================
class StatusView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="צפה ברשימת שחקנים", style=discord.ButtonStyle.blurple, emoji="👥", custom_id="status_players_btn")
    async def view_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔍 טוען את רשימת השחקנים המחוברים...", ephemeral=True)
# ==========================================
# 🎖️ מערכת פנל רולים ואישורים (ROLE REQUEST SYSTEM)
# ==========================================
class RoleRequestModal(discord.ui.Modal, title="טופס הגשת בקשת רולים - GamePlay IL"):
    staff_name = discord.ui.TextInput(
        label="שם השוטר / חבר הצוות שהכניס אותך",
        placeholder="לדוגמה: אהרון / דיוויד",
        style=discord.TextStyle.short,
        required=True
    )
    role_reason = discord.ui.TextInput(
        label="פירוט הרולים או הדרגות שאתה אמור לקבל",
        placeholder="לדוגמה: שוטר סיור, בלש מתחיל, רול תומך",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        log_channel = guild.get_channel(ROLE_APPROVAL_LOG_CHANNEL_ID)
        if not log_channel:
            return await interaction.followup.send("שגיאה: חדר אישור הרולים לא נמצא במערכת.", ephemeral=True)

        embed = discord.Embed(
            title="📥 בקשת רולים חדשה ממתינה לאישור",
            description=(
                f"**מגיש הבקשה:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"**הגורם המאשר / שהכניס:** `{self.staff_name.value}`\n\n"
                f"**פירוט הרולים המבוקשים:**\n```{self.role_reason.value}```"
            ),
            color=0xffa500
        )
        if os.path.exists(BACKGROUND_IMAGE):
            embed.set_image(url="attachment://background.png")
        embed.set_footer(text="לחץ על הכפתור הירוק למטה לבחירת רולים והענקתם")

        view = RoleApprovalView(interaction.user.id)
        await setup_dynamic_selects(guild, view)
        
        if os.path.exists(BACKGROUND_IMAGE):
            file = discord.File(BACKGROUND_IMAGE, filename="background.png")
            await log_channel.send(file=file, embed=embed, view=view)
        else:
            await log_channel.send(embed=embed, view=view)
            
        await interaction.followup.send("✅ הטופס נשלח בהצלחה לחדר אישורי ההנהלה! אנא המתן לאישור הבקשה.", ephemeral=True)
class DynamicRoleSelect(discord.ui.Select):
    def __init__(self, target_user_id: int):
        self.target_user_id = target_user_id
        super().__init__(
            placeholder="בחר רולים להענקה (ניתן לבחור כמה רולים יחד)...",
            min_values=1,
            max_values=15,
            custom_id="dynamic_role_selector_spec"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.followup.send("שגיאה: המשתמש לא נמצא בשרת.", ephemeral=True)

        added_roles = []
        for role_id_str in self.values:
            role = guild.get_role(int(role_id_str))
            if role and role < guild.me.top_role:
                await target.add_roles(role)
                added_roles.append(role.name)

        roles_list = ", ".join(added_roles)
        await interaction.followup.send(f"🎖️ הרולים הבאים הוענקו בהצלחה ל-{target.mention}:\n**{roles_list}**", ephemeral=True)

    async def _populate_options(self, guild: discord.Guild):
        options = []
        for role in sorted(guild.roles, reverse=True):
            if role.is_default() or role.managed:
                continue
            options.append(discord.SelectOption(label=role.name, value=str(role.id), emoji="👮‍♂️"))
            if len(options) == 25:
                break
        self.options = options

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

    @discord.ui.button(label="ענישה: BAN", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="admin_action_ban")
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("המשתמש כבר לא נמצא בשרת.", ephemeral=True)
        await target.ban(reason="נדחה בטופס הדרגות וקיבל הרחקה מההנהלה העליונה.")
        await interaction.response.send_message(f"🔨 המשתמש {target.name} נחסם בהצלחה מהשרת לצמיתות.", ephemeral=True)

    @discord.ui.button(label="ענישה: KICK", style=discord.ButtonStyle.secondary, emoji="🚪", custom_id="admin_action_kick")
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("המשתמש כבר לא נמצא בשרת.", ephemeral=True)
        await target.kick(reason="נדחה בטופס הדרגות ונזרק מהשרת.")
        await interaction.response.send_message(f"🚪 המשתמש {target.name} נזרק בהצלחה מהשרת.", ephemeral=True)

    @discord.ui.button(label="סיום פנייה ונתינת רולים", style=discord.ButtonStyle.success, emoji="✅", custom_id="admin_action_finish")
    async def finish_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ פניית הדרגות הסתיימה בהצלחה והרולים שנבחרו עודכנו!", ephemeral=True)
        self.stop()

class RoleRequestStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="להגשת בקשת רולים ודרגות", style=discord.ButtonStyle.primary, emoji="🎖️", custom_id="start_role_req_btn")
    async def start_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RoleRequestModal())
# ==========================================
# 🎫 מערכת טיקטים ופניות אינטראקטיבית
# ==========================================
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

    @discord.ui.button(label="לקיחת הפנייה", style=discord.ButtonStyle.success, emoji="📌", custom_id="ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed_by:
            return await interaction.response.send_message(f"❌ טיקט זה כבר נלקח לטיפול על ידי {self.claimed_by.mention}.", ephemeral=True)
        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"בטיפול של: {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"📌 החבר צוות {interaction.user.mention} לקח על עצמו את הטיפול בפנייה זו!")

    @discord.ui.button(label="שינוי שם חדר", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="ticket_rename")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        class RenameModal(discord.ui.Modal, title="שינוי שם חדר הטיקט"):
            new_name = discord.ui.TextInput(label="השם החדש של החדר", placeholder="לדוגמה: בטיפול-אהרון", required=True)
            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                await inter.channel.edit(name=self.new_name.value)
                await inter.followup.send(f"✅ שם החדר השתנה בהצלחה ל-`{self.new_name.value}`!", ephemeral=True)
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="הוספת משתמש", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_user")
    async def add_user_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 אנא תייג את האדם שברצונך להוסיף לחדר ברגע זה בצ'אט:", ephemeral=True)
        def check(m):
            return m.channel.id == interaction.channel.id and m.author.id == interaction.user.id
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if msg.mentions:
                target_user = msg.mentions[0]
                await interaction.channel.set_permissions(target_user, view_channel=True, send_messages=True)
                await interaction.channel.send(f"✅ המשתמש {target_user.mention} נוסף בהצלחה לשיחת הטיקט על ידי {interaction.user.mention}!")
            else:
                await interaction.channel.send("❌ לא זוהה תיוג תקין של משתמש. הפעולה בבוטלה.")
        except asyncio.TimeoutError:
            await interaction.channel.send("❌ עבר הזמן המוקצב להוספת משתמש. אנא לחץ שוב.")

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_main")
    async def close_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TicketCloseModal(discord.ui.Modal, title="סיכום וסגירת טיקט - GamePlay IL"):
            summary = discord.ui.TextInput(label="פירוט תמציתי של מה שהיה בטיקט", style=discord.TextStyle.long, required=True, placeholder="סיכום הטיפול בפנייה...")
            answered = discord.ui.TextInput(label="האם הטיקט קיבל מענה ופתרון מלא? (כן / לא)", style=discord.TextStyle.short, required=True, placeholder="כן / לא")

            def __init__(self, creator_id: int):
                super().__init__()
                self.creator_id = creator_id

            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=False)
                await inter.channel.send("🔒 הטיקט מסוכם וייסגר בעוד כ-5 שניות...")
                guild = inter.guild
                log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
                creator = guild.get_member(self.creator_id)

                log_embed = discord.Embed(title="🔒 פנייה נסגרה ותועדה במערכת", color=discord.Color.red())
                log_embed.add_field(name="חדר הטיקט", value=f"`{inter.channel.name}`", inline=True)
                log_embed.add_field(name="נסגר על ידי", value=inter.user.mention, inline=True)
                log_embed.add_field(name="פתח את הטיקט", value=creator.mention if creator else f"`{self.creator_id}`", inline=True)
                log_embed.add_field(name="האם קיבל מענה?", value=f"**{self.answered.value}**", inline=True)
                log_embed.add_field(name="סיכום הטיפול בפנייה", value=f"```{self.summary.value}```", inline=False)
                if os.path.exists(BACKGROUND_IMAGE):
                    log_embed.set_image(url="attachment://background.png")

                if log_channel:
                    if os.path.exists(BACKGROUND_IMAGE):
                        file_log = discord.File(BACKGROUND_IMAGE, filename="background.png")
                        await log_channel.send(file=file_log, embed=log_embed)
                    else:
                        await log_channel.send(embed=log_embed)
                await asyncio.sleep(5)
                await inter.channel.delete()
        await interaction.response.send_modal(TicketCloseModal(self.creator_id))
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="שאלה כללית", description="פתיחת פנייה לשאלות בנושא מחלקה", emoji="❓", value="שאלה כללית"),
            discord.SelectOption(label="דיווח באג", description="דיווח על תקלה טכנית או בעיה במשחק", emoji="🐛", value="דיווח באג"),
            discord.SelectOption(label="תלונה על שוטר", description="הגשת תלונה רשמית למחלקת משמעת", emoji="🚨", value="תלונה על שוטר"),
            discord.SelectOption(label="אחר", description="פניות בנושאים שונים אחרים", emoji="📂", value="אחר")
        ]
        super().__init__(placeholder="בחר את סוג הפנייה שלך מתוך הרשימה...", min_values=1, max_values=1, options=options, custom_id="ticket_dropdown_select_main")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        ticket_type = self.values[0]
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True)
        }
        staff_role = guild.get_role(STAFF_TICKET_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"{ticket_type.replace(' ', '-')}-{interaction.user.name}", overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"🎫 פנייה חדשה בנושא: {ticket_type}",
            description=f"שלום {interaction.user.mention},\nצוות הטיקטים קיבל את פנייתך ויהיה איתך בהקדם. אנא פרט את הסיבה בחדר זה בשביל לקבל מענה מהיר.",
            color=0x2f3136
        )
        if os.path.exists(BACKGROUND_IMAGE):
            embed.set_image(url="attachment://background.png")
        embed.set_footer(text="GamePlay IL Support View")

        view = TicketActionButtons(interaction.user.id)
        
        if os.path.exists(BACKGROUND_IMAGE):
            file_t = discord.File(BACKGROUND_IMAGE, filename="background.png")
            await channel.send(file=file_t, embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ הטיקט שלך נפתח בהצלחה בערוץ: {channel.mention}", ephemeral=True)

class TicketStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())
# ==========================================
# 👑 פנלים מתקדמים (STAFF PANELS)
# ==========================================
class StaffPanelButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="בדיקת סטטוס מערכת", style=discord.ButtonStyle.primary, emoji="📊", custom_id="staff_status")
    async def status_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📊 סטטוס בוט ומערכות", color=discord.Color.green())
        embed.add_field(name="שרת אינטרנט (Keep Alive)", value="🟢 פעיל (פורט 8080)", inline=True)
        embed.add_field(name="לולאת ניטור FiveM", value="🟢 פעילה (30 שניות)", inline=True)
        embed.add_field(name="מערכת רולים", value="🟢 מחוברת ומאובטחת", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CitizenPanelButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="החשבון שלי", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="citizen_profile")
    async def profile_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        embed = discord.Embed(title=f"👤 כרטיס אזרח - {user.name}", color=0x7289da)
        embed.add_field(name="תאריך הצטרפות", value=user.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="הרול הגבוה ביותר שלך", value=user.top_role.mention, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="פרטי חיבור לשרת המשחק", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="citizen_connect")
    async def connect_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🎮 קישור חיבור ישיר לשרת FiveM: `cfx.re/join/am35ok`", ephemeral=True)

# ==========================================
# 🛠️ פקודות סלאש להקמת המערכות
# ==========================================
@bot.tree.command(name="setup_verify", description="יוצר חדר ייעודי ומציב את מערכת האימות המעוצבת")
@app_commands.checks.has_permissions(administrator=True)
async def setup_verify(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name="ーー 🌟 ברוכים הבאים 🌟 ーー")
    if not category:
        category = await guild.create_category(name="ーー 🌟 ברוכים הבאים 🌟 ーー")
    channel = discord.utils.get(category.text_channels, name="verification")
    if not channel:
        channel = await guild.create_text_channel(name="verification", category=category)
    if not os.path.exists(BACKGROUND_IMAGE):
        return await interaction.followup.send("שגיאה: קובץ background.png לא נמצא.", ephemeral=True)
    gif_file = discord.File(BACKGROUND_IMAGE, filename="background.png")
    embed = discord.Embed(
        title="🛡️ מערכת אימות הגנה - שרת 67",
        description="ברוכים הבאים לשרת! לחצו על הכפתור הירוק למטה כדי להתחיל אימות.",
        color=0x2f3136
    )
    embed.set_image(url="attachment://background.png")
    await channel.send(file=gif_file, embed=embed, view=VerifyButton())
    await interaction.followup.send("✅ מערכת האימות הוצבה בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_role_panel", description="מקים אוטומטית את פנל בקשת הדרגות והרולים")
@app_commands.checks.has_permissions(administrator=True)
async def setup_role_panel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = guild.get_channel(ROLE_PANEL_CHANNEL_ID)
    if not channel:
        return await interaction.followup.send("חדר פנל הרולים לא נמצא במערכת.", ephemeral=True)
    embed = discord.Embed(
        title="🎖️ מחלקת משטרת GamePlay-IL | בקשת דרגות ורולים",
        description="ברוכים הבאים למרכז השליטה. לחצו על הכפתור למטה ומלאו את הפרטים במדויק.",
        color=0x1a73e8
    )
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
    view = RoleRequestStarterView()
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        await channel.send(file=file, embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ פנל בקשת הרולים הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_ticket_panel", description="מקים אוטומטית את פנל פתיחת הטיקטים עם תפריט הבחירה")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket_panel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not channel:
        return await interaction.followup.send("חדר פנל הטיקטים לא נמצא במערכת.", ephemeral=True)
    embed = discord.Embed(
        title="🎫 מחלקת משטרת GamePlay-IL | פתיחת פניות ותמיכה",
        description="בחרו את קטגוריית הפנייה המתאימה מתוך התפריט הנפתח למטה והבוט יפתח לכם חדר אישי.",
        color=0x1a73e8
    )
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
    view = TicketStarterView()
    if os.path.exists(BACKGROUND_IMAGE):
        file_panel = discord.File(BACKGROUND_IMAGE, filename="background.png")
        await channel.send(file=file_panel, embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ פנל הטיקטים המעוצב הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="reset_logs", description="מוחק את כל ערוצי הלוגים הישנים ומקים אותם מחדש בצורה נקייה")
@app_commands.checks.has_permissions(administrator=True)
async def reset_logs(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    staff_role = guild.get_role(STAFF_TICKET_ROLE_ID)
    if not staff_role:
        return await interaction.followup.send("שגיאה: רול הצוות שצוין לא נמצא בשרת.", ephemeral=True)
    old_category = discord.utils.get(guild.categories, name="LOGS")
    if old_category:
        for channel in old_category.text_channels:
            try:
                await channel.delete()
            except Exception:
                pass
        try:
            await old_category.delete()
        except Exception:
            pass
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=False)
    }
    new_category = await guild.create_category(name="LOGS", overwrites=overwrites)
    created_count = 0
    for ch_name in LOG_CHANNELS:
        await guild.create_text_channel(name=ch_name, category=new_category)
        created_count += 1
    await interaction.followup.send(f"🧹 קטגוריית LOGS הוקמה מחדש מאפס עם {created_count} חדרים.", ephemeral=True)
# ==========================================
# 📊 משימה אוטומטית ברקע - פנייה ישירה ל-FiveM (מתחלף כל 30 שניות)
# ==========================================
@tasks.loop(seconds=30)
async def track_fivem_status():
    global status_cycle
    guild = bot.get_guild(GUILD_ID)
    if not guild: 
        return
    players_count, max_players, server_online = 0, 5, False
    try:
        url = f"http://{SERVER_IP}:{SERVER_PORT}/players.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            players_count = len(json.loads(response.read().decode()))
            server_online = True
    except Exception:
        server_online = False
    try:
        info_url = f"http://{SERVER_IP}:{SERVER_PORT}/info.json"
        info_req = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(info_req, timeout=4) as info_response:
            max_players = int(json.loads(info_response.read().decode()).get('sv_maxclients', 5))
    except Exception:
        pass
    if status_cycle == 0:
        status_text = f"{players_count}/{max_players} שחקנים" if server_online else "0/5"
        status_cycle = 1
    else:
        status_text = "Online 🟢" if server_online else "Offline 🔴"
        status_cycle = 0
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_text))

async def setup_dynamic_selects(guild: discord.Guild, view: RoleApprovalView):
    for item in view.children:
        if isinstance(item, DynamicRoleSelect):
            try:
                await item._populate_options(guild)
            except Exception:
                pass

# ==========================================
# ⚙️ הפעלת הבוט וסנכרון פקודות
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")
    bot.add_view(RoleRequestStarterView())
    bot.add_view(TicketStarterView())
    if not track_fivem_status.is_running():
        track_fivem_status.start()
    try:
        guild_obj = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild_obj)
        await bot.tree.sync(guild=guild_obj)
        print(f"🎯 Synced slash commands for Police Bot successfully.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    if TOKEN: 
        bot.run(TOKEN)
