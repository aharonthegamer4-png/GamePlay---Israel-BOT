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
# 📊 משימה אוטומטית ברקע - ניטור IP וסטטוס FiveM
# ==========================================

@tasks.loop(seconds=30)
async def track_fivem_status():
    global status_cycle
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    players_count = 0
    max_players = 5
    server_online = False

    # פנייה ישירה לכתובת ה-IP הציבורית של השרת שלכם
    try:
        url = f"http://{SERVER_IP}:{SERVER_PORT}/players.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            players_count = len(data)
            server_online = True

        info_url = f"http://{SERVER_IP}:{SERVER_PORT}/info.json"
        info_req = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(info_req, timeout=4) as info_response:
            info_data = json.loads(info_response.read().decode())
            max_players = int(info_data.get('sv_maxclients', 5))
    except Exception:
        server_online = False

    # לוגיקת החלפה חכמה כל 30 שניות ללא ניחושים
    if status_cycle == 0:
        # סטטוס 1: כמות שחקנים אמיתית בלייב
        status_text = f"{players_count}/{max_players} שחקנים" if server_online else "0/5"
        status_cycle = 1
    else:
        # סטטוס 2: מצב השרת - אונליין או אופליין
        status_text = "Online 🟢" if server_online else "Offline 🔴"
        status_cycle = 0

    activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
    await bot.change_presence(activity=activity)
# ==========================================
# 👋 מערכת ברוכים הבאים (WELCOME SYSTEM)
# ==========================================

@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != GUILD_ID:
        return
        
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title="✨ חבר חדש הצטרף למחלקת המשטרה!",
        description=(
            f"ברוך הבא {member.mention} אל השרת הרשמי של **GamePlay IL**!\n\n"
            f"➔ אתה החבר ה-**{len(member.guild.members)}** בקהילה.\n"
            f"➔ אנא היכנס לערוץ האימות או פתח פנייה לקבלת דרגות שירות."
        ),
        color=0x1a73e8
    )
    
    # שימוש ישיר ורשמי בקובץ ה-PNG שהעלית ב-GitHub כרקע קבוע
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
        
    embed.set_footer(text=f"GamePlay IL | Security & Automation Engine", icon_url=member.guild.icon.url if member.guild.icon else None)

    if os.path.exists(BACKGROUND_IMAGE):
        await channel.send(file=file, embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")
    else:
        await channel.send(embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")
# ==========================================
# 🎖️ מערכת פנל רולים ואישורים (ROLE REQUEST SYSTEM)
# ==========================================

# הטופס הדיגיטלי הנפתח לאזרח כשהוא לוחץ על כפתור הגשת בקשת רולים
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
        
        # משיכת חדר הלוגים לאישור הדרגות
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

        # יצירת המערכת האינטראקטיבית למורשי האישור (תפריטי בחירה + כפתורי ענישה)
        view = RoleApprovalView(interaction.user.id)
        
        if os.path.exists(BACKGROUND_IMAGE):
            file = discord.File(BACKGROUND_IMAGE, filename="background.png")
            await log_channel.send(file=file, embed=embed, view=view)
        else:
            await log_channel.send(embed=embed, view=view)
            
        await interaction.followup.send("✅ הטופס נשלח בהצלחה לחדר אישורי ההנהלה! אנא המתן לאישור הבקשה.", ephemeral=True)
# תפריט הבחירה והכפתורים שמופיעים בחדר אישורי הדרגות עבור מורשי ההנהלה
class RoleApprovalView(discord.ui.View):
    def __init__(self, target_user_id: int):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        # הוספת תפריט הבחירה הדינמי שמציג את כל הרולים בשרת
        self.add_item(DynamicRoleSelect(target_user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # הגנה: רק מי שיש לו את רול אישור הדרגות יכול לגעת בכפתורים
        if ROLE_APPROVER_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ אין לך את ההרשאות הדרושות לביצוע פעולות בפנל זה.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ענישה: BAN", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="admin_action_ban")
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("המשתמש כבר לא נמצא בשרת הדיסקורד.", ephemeral=True)
        
        await target.ban(reason="נדחה בטופס הדרגות וקיבל הרחקה מההנהלה העליונה.")
        await interaction.response.send_message(f"🔨 המשתמש {target.name} נחסם בהצלחה מהשרת לצמיתות.", ephemeral=True)

    @discord.ui.button(label="ענישה: KICK", style=discord.ButtonStyle.secondary, emoji="🚪", custom_id="admin_action_kick")
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("המשתמש כבר לא נמצא בשרת הדיסקורד.", ephemeral=True)
        
        await target.kick(reason="נדחה בטופס הדרגות ונזרק מהשרת.")
        await interaction.response.send_message(f"🚪 המשתמש {target.name} נזרק בהצלחה מהשרת.", ephemeral=True)

    @discord.ui.button(label="סיום פנייה ונתינת רולים", style=discord.ButtonStyle.success, emoji="✅", custom_id="admin_action_finish")
    async def finish_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        # כפתור סיום הפנייה בלי למחוק את החדר כפי שביקשת
        await interaction.response.send_message("✅ פניית הדרגות הסתיימה בהצלחה והרולים שנבחרו עודכנו!", ephemeral=True)
        self.stop()

# תפריט הבחירה הדינמי - שולף לבד את כל הרולים הקיימים בשרת שלך בלייב!
class DynamicRoleSelect(discord.ui.Select):
    def __init__(self, target_user_id: int):
        self.target_user_id = target_user_id
        super().__init__(
            placeholder="בחר רולים להענקה (ניתן לבחור כמה רולים יחד)...",
            min_values=1,
            max_values=15, # מאפשר לבחור עד 15 רולים במקביל במכה אחת
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
            if role and role < guild.me.top_role: # מוודא שהבוט לא מנסה לתת רול שגבוה ממנו
                await target.add_roles(role)
                added_roles.append(role.name)

        roles_list = ", ".join(added_roles)
        await interaction.followup.send(f"🎖️ הרולים הבאים הוענקו בהצלחה ל-{target.mention}:\n**{roles_list}**", ephemeral=True)

    # פונקציה שמופעלת אוטומטית כשהפנל נשלח כדי למלא את התפריט ברולים האמיתיים מהשרת
    async def _populate_options(self, guild: discord.Guild):
        options = []
        # לוקח את כל הרולים בשרת, מסנן את ה-Everyone ואת הרולים של הבוטים
        for role in sorted(guild.roles, reverse=True):
            if role.is_default() or role.managed:
                continue
            options.append(discord.SelectOption(label=role.name, value=str(role.id), emoji="👮‍♂️"))
            if len(options) == 25: # מגבלת דיסקורד מקסימלית לתפריט בחירה בודד
                break
        self.options = options
# הפנל הראשי שבו האזרח לוחץ ונפתח לו הטופס
class RoleRequestStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="להגשת בקשת רולים ודרגות", style=discord.ButtonStyle.primary, emoji="🎖️", custom_id="start_role_req_btn")
    async def start_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        # פתיחת הטופס הדיגיטלי (Modal) שהגדרנו בחלק 4
        await interaction.response.send_modal(RoleRequestModal())

# פקודת ההקמה לפנל הרולים
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
        description="ברוכים הבאים למרכז השליטה וניהול כוח האדם. במידה וגוייסתם למחלקה או שאתם זכאים להעלאה בדרגה - לחצו על הכפתור למטה ומלאו את הפרטים במדויק.",
        color=0x1a73e8
    )
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
    embed.set_footer(text="GamePlay IL Security System")

    view = RoleRequestStarterView()
    
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        await channel.send(file=file, embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    await interaction.followup.send(f"✅ פנל בקשת הרולים הוקם בהצלחה בחדר {channel.mention}!", ephemeral=True)


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
        # הגנה: מונע לקיחה כפולה, רק הראשון שתופס זוכה
        if self.claimed_by:
            return await interaction.response.send_message(f"❌ טיקט זה כבר נלקח לטיפול על ידי {self.claimed_by.mention}.", ephemeral=True)
        
        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"בטיפול של: {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"📌 החבר צוות {interaction.user.mention} לקח על עצמו את הטיפול בפנייה זו!")

    @discord.ui.button(label="שינוי שם חדר", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="ticket_rename")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # שינוי שם לטיקט באמצעות טופס מהיר
        class RenameModal(discord.ui.Modal, title="שינוי שם חדר הטיקט"):
            new_name = discord.ui.TextInput(label="השם החדש של החדר (באותיות קטנות / אנגלית / עברית)", placeholder="לדוגמה: בטיפול-אהרון", required=True)
            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                await inter.channel.edit(name=self.new_name.value)
                await inter.followup.send(f"✅ שם החדר השתנה בהצלחה ל-`{self.new_name.value}`!", ephemeral=True)
        await interaction.response.send_modal(RenameModal())
    @discord.ui.button(label="הוספת משתמש", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_user")
    async def add_user_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 אנא תייג (Mention) את האדם שברצונך להוסיף לחדר ברגע זה בצ'אט:", ephemeral=True)
        
        def check(m):
            return m.channel.id == interaction.channel.id and m.author.id == interaction.user.id
            
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if msg.mentions:
                target_user = msg.mentions[0]
                await interaction.channel.set_permissions(target_user, view_channel=True, send_messages=True)
                await interaction.channel.send(f"✅ המשתמש {target_user.mention} נוסף בהצלחה לשיחת הטיקט על ידי {interaction.user.mention}!")
            else:
                await interaction.channel.send("❌ לא זוהה תיוג תקין של משתמש. הפעולה בוטלה.")
        except asyncio.TimeoutError:
            await interaction.channel.send("❌ עבר הזמן המוקצב להוספת משתמש. אנא לחץ שוב במידת הצורך.")

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_main")
    async def close_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # טופס סגירה שמבקש פירוט מלא של הטיקט כפי שביקשת
        class TicketCloseModal(discord.ui.Modal, title="סיכום וסגירת טיקט - GamePlay IL"):
            summary = discord.ui.TextInput(label="פירוט תמציתי של מה שהיה בטיקט", style=discord.TextStyle.long, required=True, placeholder="רשום כאן את סיכום הטיפול בפנייה...")
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

                # שליחת לוג מעוצב ומטורף לחדר הלוגים שציינת
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


# תפריט הבחירה הראשי לפתיחת טיקטים (Select Menu)
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="שאלה כללית", description="פתיחת פנייה לשאלות בנושא מחלקה", emoji="❓", value="שאלה כללית"),
            discord.SelectOption(label="דיווח באג", description="דיווח על תקלה טכנית או בעיה במשחק", emoji="🐛", value="דיווח באג"),
            discord.SelectOption(label="תלונה על שוטר", description="הגשת תלונה רשמית למחלקת משמעת", emoji="🚨", value="תלונה על שוטר"),
            discord.SelectOption(label="אחר", description="פניות בנושאים שונים אחרים", emoji="📂", value="אחר")
        ]
        super().__init__(placeholder="בחר את סוג הפנייה שלך מתוך הרשימה...", min_values=1, max_values=1, custom_id="ticket_dropdown_select_main")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        ticket_type = self.values[0]
        
        # יצירת חדר פרטי לטיקט
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
        description="זקוקים לעזרה, רוצים לדווח על באג או להגיש תלונה? בחרו את קטגוריית הפנייה המתאימה מתוך התפריט הנפתח למטה והבוט יפתח לכם חדר אישי.",
        color=0x1a73e8
    )
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
    embed.set_footer(text="GamePlay IL Global Support")

    view = TicketStarterView()
    
    if os.path.exists(BACKGROUND_IMAGE):
        file_panel = discord.File(BACKGROUND_IMAGE, filename="background.png")
        await channel.send(file=file_panel, embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    await interaction.followup.send(f"✅ פנל הטיקטים המעוצב הוקם בהצלחה בחדר {channel.mention}!", ephemeral=True)
# סוגר של מחלקת ה-DynamicRoleSelect בשביל למלא את הרולים באונליין
# פונקציית פיתוח מתקדמת שקוראת את הרולים של השרת שלך בשביל למנוע תקלות קריסה
async def setup_dynamic_selects(guild: discord.Guild, view: RoleApprovalView):
    for item in view.children:
        if isinstance(item, DynamicRoleSelect):
            await item._populate_options(guild)

# ==========================================
# ⚙️ הפעלת הבוט וסנכרון פקודות
# ==========================================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")
    
    # השארת כל מערכות הכפתורים, הטיקטים והרולים פעילות לתמיד (Persistent Views)
    bot.add_view(RoleRequestStarterView())
    bot.add_view(TicketStarterView())
    
    # הפעלת לולאת הסטטוס של ה-FiveM החכמה
    if not track_fivem_status.is_running():
        track_fivem_status.start()
        
    try:
        guild_obj = discord.Object(id=GUILD_ID)
        # טעינה וסנכרון של כל הפקודות המשטרתיות החדשות לשרת שלכם
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
