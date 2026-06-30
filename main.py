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
SAY_COMMAND_ROLE_ID = 1521602302622961857 # הרול הבלעדי שיכול להשתמש בפקודת !say

# חדרים רשמיים בשרת
WELCOME_CHANNEL_ID = 1500997767256870922
ROLE_PANEL_CHANNEL_ID = 1500997767256870923
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
    
    if os.path.exists(BACKGROUND_IMAGE):
        file = discord.File(BACKGROUND_IMAGE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    else:
        embed.set_thumbnail(url=member.default_avatar.url)
        
    embed.set_footer(text="Developed by Aharon the gamer", icon_url=member.guild.icon.url if member.guild.icon else None)

    if os.path.exists(BACKGROUND_IMAGE):
        await channel.send(file=file, embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")
    else:
        await channel.send(embed=embed, content=f"היי {member.mention}, ברוך הבא! 👮‍♂️💎")

@bot.event
async def on_member_remove(member: discord.Member):
    if member.guild.id != GUILD_ID:
        return
        
    log_channel = member.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title="🏃‍♂️ משתמש עזב את השרת",
        description=f"המשתמש **{member.name}** ({member.mention}) עזב את שרת המשטרה ברגע זה.\n\n**מזהה משתמש:** `{member.id}`",
        color=discord.Color.red()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    else:
        embed.set_thumbnail(url=member.default_avatar.url)
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
        embed.set_footer(text="Developed by Aharon the gamer")

        view = RoleApprovalView(interaction.user.id)
        
        options = []
        for role in sorted(guild.roles, reverse=True):
            if role.is_default() or role.managed:
                continue
            options.append(discord.SelectOption(label=role.name, value=str(role.id), emoji="👮‍♂️"))
            if len(options) == 25:
                break
        
        for item in view.children:
            if isinstance(item, DynamicRoleSelect):
                item.options = options
        
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
            placeholder="בחר רולים להענקה ולנעילת הפנייה...",
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
            if role:
                try:
                    await target.add_roles(role)
                    added_roles.append(role.name)
                except discord.Forbidden:
                    pass

        if not added_roles:
            return await interaction.followup.send("❌ שגיאה: לא ניתן להעניק את הרולים. ודא שרול הבוט נמצא בטופ של רשימת הרולים!", ephemeral=True)

        roles_list = ", ".join(added_roles)
        
        # 🔒 שלב 1: נעילת הודעת הפנל המקורית על ידי מחיקת הכפתורים והתפריט לחלוטין
        old_embed = interaction.message.embeds
        locked_embed = discord.Embed(
            title="🔒 פניית בקשת רולים טופלה וננעלה",
            description=old_embed.description if old_embed else "טופס בקשת דרגות",
            color=discord.Color.green()
        )
        if os.path.exists(BACKGROUND_IMAGE):
            locked_embed.set_image(url="attachment://background.png")
            
        locked_embed.add_field(name="🛡️ סטטוס מערכת", value="✅ הרולים הוענקו, פנל השליטה הושבת וננעל לחלוטין.", inline=False)
        locked_embed.add_field(name="👮‍♂️ מנהל מטפל", value=interaction.user.mention, inline=True)
        locked_embed.add_field(name="👤 המשתמש שקיבל", value=target.mention, inline=True)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        await interaction.message.edit(embed=locked_embed, view=None)

        # 📄 שלב 2: שליחת הלוג לחדר הלוגים של הרולים
        log_channel = guild.get_channel(ROLE_GIVEN_LOG_CHANNEL_ID)
        if log_channel:
            given_embed = discord.Embed(
                title="🎖️ לוג רשמי - הענקת דרגות ורולים",
                description=(
                    f"**Action:** הענקת רולים ודרגות 🎖️\n"
                    f"**המנהל המאשר:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"**המשתמש שקיבל:** {target.mention} (`{target.id}`)\n\n"
                    f"**הרולים שהוענקו בהצלחה:**\n```{roles_list}```"
                ),
                color=0x1a73e8
            )
            given_embed.set_footer(text="Developed by Aharon the gamer")
            if os.path.exists(BACKGROUND_IMAGE):
                given_embed.set_image(url="attachment://background.png")
                file_log = discord.File(BACKGROUND_IMAGE, filename="background.png")
                await log_channel.send(file=file_log, embed=given_embed)
            else:
                await log_channel.send(embed=given_embed)

        # ✉️ שלב 3: שליחת הודעה פרטית (DM) למשתמש שהרולים שלו אושרו!
        try:
            dm_embed = discord.Embed(
                title="🚨 עדכון מחלקת המשטרה | בקשתך אושרה! ✨",
                description=(
                    f"שלום {target.mention},\n"
                    f"שמחים לעדכן אותך כי טופס בקשת הדרגות שלך בשרת **GamePlay IL** נבדק ואושר! 👮‍♂️\n\n"
                    f"**המנהל המאשר:** {interaction.user.name}\n"
                    f"**🎖️ הדרגות/רולים שקיבלת:**\n```{roles_list}```\n"
                    f"עלה והצלח בשמירה על החוק והסדר בשרת! 🚓"
                ),
                color=discord.Color.green()
            )
            dm_embed.set_footer(text="Developed by Aharon the gamer")
            await target.send(embed=dm_embed)
        except Exception:
            pass

        await interaction.followup.send(f"🎖️ הדרגות הבאות הוענקו בהצלחה, הודעת DM נשלחה והלוגים ננעלו:\n**{roles_list}**", ephemeral=True)
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
        
        try:
            try:
                dm_ban = discord.Embed(
                    title="🚨 עדכון מחלקת המשטרה | בקשתך נדחתה ❌",
                    description=(
                        f"שלום {target.name},\n"
                        f"אנא שים לב כי טופס בקשת הדרגות שלך בשרת **GamePlay IL** נדחה על ידי ההנהלה העליונה.\n"
                        f"עקב כך, הוחלט להרחיק אותך לצמידות ממערכות השרת (BAN). 🔨"
                    ),
                    color=discord.Color.red()
                )
                dm_ban.set_footer(text="Developed by Aharon the gamer")
                await target.send(embed=dm_ban)
            except Exception: pass

            await target.ban(reason="נדחה בטופס הדרגות וקיבל הרחקה מההנהלה העליונה.")
            
            old_embed = interaction.message.embeds if interaction.message.embeds else None
            locked_embed = discord.Embed(
                title="🔒 פניית בקשת רולים נדחתה וננעלה",
                description=old_embed.description if old_embed else "טופס בקשת דרגות",
                color=discord.Color.red()
            )
            if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
            locked_embed.add_field(name="🛡️ סטטוס מערכת", value="❌ המשתמש נדחה, נחסם מהשרת (BAN) ופנל השליטה הושבת.", inline=False)
            locked_embed.set_footer(text="Developed by Aharon the gamer")
            await interaction.message.edit(embed=locked_embed, view=None)

            log_channel = guild.get_channel(ROLE_GIVEN_LOG_CHANNEL_ID)
            if log_channel:
                ban_embed = discord.Embed(
                    title="🔨 לוג רשמי - חסימת משתמש מטופס דרגות",
                    description=(
                        f"**Action:** דחיית טופס וחסימה מהשרת (BAN) 🔨\n"
                        f"**המנהל המעניש:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**המשתמש שנחסם:** {target.mention} (`{target.id}`)\n"
                    ),
                    color=discord.Color.red()
                )
                ban_embed.set_footer(text="Developed by Aharon the gamer")
                if os.path.exists(BACKGROUND_IMAGE):
                    ban_embed.set_image(url="attachment://background.png")
                    await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=ban_embed)
                else:
                    await log_channel.send(embed=ban_embed)

            await interaction.response.send_message(f"🔨 המשתמש {target.name} נחסם בהצלחה והפנל ננעל.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ שגיאה: לבוט אין הרשאה לחסום משתמש זה.", ephemeral=True)

    @discord.ui.button(label="ענישה: KICK", style=discord.ButtonStyle.secondary, emoji="🚪", custom_id="admin_action_kick")
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        target = guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("המשתמש כבר לא נמצא בשרת.", ephemeral=True)
        
        try:
            try:
                dm_kick = discord.Embed(
                    title="🚨 עדכון מחלקת המשטרה | בקשתך נדחתה ❌",
                    description=(
                        f"שלום {target.name},\n"
                        f"אנא שים לב כי טופס בקשת הדרגות שלך בשרת **GamePlay IL** נדחה על ידי ההנהלה העליונה.\n"
                        f"עקב כך, הוחלט לנתק אותך ממערכות השרת הנוכחיות (KICK). 🚪"
                    ),
                    color=discord.Color.orange()
                )
                dm_kick.set_footer(text="Developed by Aharon the gamer")
                await target.send(embed=dm_kick)
            except Exception: pass

            await target.kick(reason="נדחה בטופס הדרגות ונזרק מהשרת.")
            
            old_embed = interaction.message.embeds if interaction.message.embeds else None
            locked_embed = discord.Embed(
                title="🔒 פניית בקשת רולים נדחתה וננעלה",
                description=old_embed.description if old_embed else "טופס בקשת דרגות",
                color=discord.Color.orange()
            )
            if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
            locked_embed.add_field(name="🛡️ סטטוס מערכת", value="🚪 המשתמש נדחה, נזרק מהשרת (KICK) ופנל השליטה הושבת.", inline=False)
            locked_embed.set_footer(text="Developed by Aharon the gamer")
            await interaction.message.edit(embed=locked_embed, view=None)

            log_channel = guild.get_channel(ROLE_GIVEN_LOG_CHANNEL_ID)
            if log_channel:
                kick_embed = discord.Embed(
                    title="🚪 לוג רשמי - קיק למשתמש מטופס דרגות",
                    description=(
                        f"**Action:** דחיית טופס וקיק מהשרת (KICK) 🚪\n"
                        f"**המנהל המעניש:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**המשתמש שנזרק:** {target.mention} (`{target.id}`)\n"
                    ),
                    color=discord.Color.orange()
                )
                kick_embed.set_footer(text="Developed by Aharon the gamer")
                if os.path.exists(BACKGROUND_IMAGE):
                    kick_embed.set_image(url="attachment://background.png")
                    await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=kick_embed)
                else:
                    await log_channel.send(embed=kick_embed)

            await interaction.response.send_message(f"🚪 המשתמש {target.name} נזרק בהצלחה והפנל ננעל.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ שגיאה: לבוט אין הרשאה לזרוק משתמש זה.", ephemeral=True)

    @discord.ui.button(label="סיום פנייה ונתינת רולים", style=discord.ButtonStyle.success, emoji="✅", custom_id="admin_action_finish")
    async def finish_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        old_embed = interaction.message.embeds if interaction.message.embeds else None
        locked_embed = discord.Embed(
            title="🔒 פניית בקשת רולים נסגרה ידנית",
            description=old_embed.description if old_embed else "טופס בקשת דרגות",
            color=discord.Color.green()
        )
        if os.path.exists(BACKGROUND_IMAGE): locked_embed.set_image(url="attachment://background.png")
        locked_embed.add_field(name="🛡️ סטטוס פנייה", value=f"✅ נסגר ידנית על ידי {interaction.user.mention}!", inline=False)
        locked_embed.set_footer(text="Developed by Aharon the gamer")
        
        await interaction.message.edit(embed=locked_embed, view=None)
        await interaction.response.send_message("✅ הפנייה נסגרה ותפריט השליטה הוסר מהערוץ!", ephemeral=True)
        self.stop()

class RoleRequestStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="להגשת בקשת רולים ודרגות", style=discord.ButtonStyle.primary, emoji="🎖️", custom_id="start_role_req_btn")
    async def start_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RoleRequestModal())
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
            new_name = discord.ui.TextInput(label="השם החדש של החדר", placeholder="בטיפול-אהרון", required=True)
            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                await inter.channel.edit(name=self.new_name.value)
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="הוספת משתמש", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_user")
    async def add_user_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 אנא תייג או רשום מזהה ID של האדם שברצונך להוסיף לחדר ברגע זה בצ'אט:", ephemeral=True)
        def check(m):
            return m.channel.id == interaction.channel.id and m.author.id == interaction.user.id
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            target_user = None
            
            if msg.mentions:
                target_user = msg.mentions[0]
            else:
                match = re.search(r'\d+', msg.content)
                if match:
                    target_user = interaction.guild.get_member(int(match.group()))

            if target_user:
                await interaction.channel.set_permissions(target_user, view_channel=True, send_messages=True, attach_files=True)
                await interaction.channel.send(f"✅ המשתמש {target_user.mention} נוסף בהצלחה לשיחת הטיקט על ידי {interaction.user.mention}!")
                try: await msg.delete()
                except Exception: pass
            else:
                await interaction.channel.send("❌ שגיאה: לא זוהה תיוג או ID תקין של משתמש בשרת. הפעולה בבוטלה.")
        except asyncio.TimeoutError:
            await interaction.channel.send("❌ עבר הזמן המוקצב להוספת משתמש. אנא לחץ שוב.")

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_main")
    async def close_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TicketCloseModal(discord.ui.Modal, title="סיכום וסגירת טיקט"):
            summary = discord.ui.TextInput(label="פירוט תמציתי של מה שהיה בטיקט", style=discord.TextStyle.long, required=True)
            answered = discord.ui.TextInput(label="האם הטיקט קיבל מענה מלא? (כן / לא)", required=True)

            def __init__(self, creator_id_val: int):
                super().__init__()
                self.creator_id_val = creator_id_val

            async def on_submit(self, inter: discord.Interaction):
                await inter.response.defer(ephemeral=False)
                guild = inter.guild
                log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
                creator = guild.get_member(self.creator_id_val)

                log_embed = discord.Embed(title="🔒 פנייה נסגרה ותועדה במערכת", color=discord.Color.red())
                log_embed.add_field(name="חדר הטיקט", value=f"`{inter.channel.name}`", inline=True)
                log_embed.add_field(name="נסגר על ידי", value=inter.user.mention, inline=True)
                log_embed.add_field(name="פתח את הטיקט", value=creator.mention if creator else f"`{self.creator_id_val}`", inline=True)
                log_embed.add_field(name="מענה", value=self.answered.value, inline=True)
                log_embed.add_field(name="סיכום הטיפול בפנייה", value=f"```{self.summary.value}```", inline=False)
                log_embed.set_footer(text="Developed by Aharon the gamer")
                if os.path.exists(BACKGROUND_IMAGE): log_embed.set_image(url="attachment://background.png")

                if log_channel:
                    if os.path.exists(BACKGROUND_IMAGE):
                        await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=log_embed)
                    else:
                        await log_channel.send(embed=log_embed)
                await asyncio.sleep(3)
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
        
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True)}
        staff_role = guild.get_role(STAFF_TICKET_ROLE_ID)
        if staff_role: overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"{ticket_type.replace(' ', '-')}-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title=f"🎫 פנייה חדשה בנושא: {ticket_type}", description="צוות הטיקטים יהיה איתך בהקדם.", color=0x2f3136)
        embed.set_footer(text="Developed by Aharon the gamer")
        if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")

        if os.path.exists(BACKGROUND_IMAGE):
            await channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=TicketActionButtons(interaction.user.id))
        else:
            await channel.send(embed=embed, view=TicketActionButtons(interaction.user.id))
        await interaction.response.send_message(f"✅ הטיקט שלך נפתח בהצלחה בערוץ: {channel.mention}", ephemeral=True)

class TicketStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ==========================================
# 🛠️ פקודות טקסט רגילות (!) להקמת המערכות
# ==========================================
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
    guild = ctx.guild
    channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not channel: return await ctx.send("❌ חדר פנל הטיקטים לא נמצא.")
    
    embed = discord.Embed(title="🎫 מחלקת משטרת GamePlay-IL | פתיחת פניות ותמיכה", description="בחרו את קטגוריית הפנייה המתאימה מתוך התפריט.", color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): embed.set_image(url="attachment://background.png")
    
    view = TicketStarterView()
    if os.path.exists(BACKGROUND_IMAGE):
        await channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)
    try: await ctx.message.delete()
    except Exception: pass
# ==========================================
# 📢 פקודת !say המאובטחת והנעולה לרול שלכם בלבד!
# ==========================================
@bot.command(name="say")
async def say_command(ctx, *, message: str = None):
    has_role = any(role.id == SAY_COMMAND_ROLE_ID for role in ctx.author.roles)
    if not has_role: return
        
    if not message:
        return await ctx.send(f"❌ שגיאה: אנא רשום טקסט לאחר הפקודה.", delete_after=5)

    try: await ctx.message.delete()
    except Exception: pass

    embed = discord.Embed(description=message, color=0x1a73e8)
    embed.set_footer(text="Developed by Aharon the gamer")
    
    if os.path.exists(BACKGROUND_IMAGE):
        embed.set_image(url="attachment://background.png")
        await ctx.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
    else:
        await ctx.send(embed=embed)

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
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.guild.id != GUILD_ID: return
    log_channel = before.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log_channel: return

    if len(before.roles) < len(after.roles):
        new_role = next(role for role in after.roles if role not in before.roles)
        responsible_user = "מערכת דיסקורד / בוט"
        try:
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    responsible_user = entry.user.mention
                    break
        except Exception: pass
        embed = discord.Embed(title="🟢 רול הוענק למשתמש", description=f"**המשתמש שקיבל:** {after.mention}\n**המשנה:** {responsible_user}\n\n**הרול:** {new_role.mention}", color=discord.Color.green())
        embed.set_footer(text="Developed by Aharon the gamer")
        if os.path.exists(BACKGROUND_IMAGE): await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
        else: await log_channel.send(embed=embed)

    elif len(before.roles) > len(after.roles):
        removed_role = next(role for role in before.roles if role not in after.roles)
        responsible_user = "מערכת דיסקורד / בוט"
        try:
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    responsible_user = entry.user.mention
                    break
        except Exception: pass
        embed = discord.Embed(title="🔴 רול הוסר ממשתמש", description=f"**המשתמש:** {after.mention}\n**המשנה:** {responsible_user}\n\n**הרול שהוסר:** {removed_role.mention}", color=discord.Color.red())
        embed.set_footer(text="Developed by Aharon the gamer")
        if os.path.exists(BACKGROUND_IMAGE): await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
        else: await log_channel.send(embed=embed)

@bot.event
async def on_guild_role_create(role: discord.Role):
    if role.guild.id != GUILD_ID: return
    log_channel = role.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log_channel: return
    responsible_user = "מנהל שרת"
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            responsible_user = entry.user.mention
            break
    except Exception: pass
    embed = discord.Embed(title="✨ רול חדש נוצר", description=f"**נוצר על ידי:** {responsible_user}\n**שם הרול:** `{role.name}`", color=discord.Color.blue())
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
    else: await log_channel.send(embed=embed)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    if role.guild.id != GUILD_ID: return
    log_channel = role.guild.get_channel(SERVER_AUDIT_LOG_CHANNEL_ID)
    if not log_channel: return
    responsible_user = "מנהל שרת"
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            responsible_user = entry.user.mention
            break
    except Exception: pass
    embed = discord.Embed(title="🗑️ רול נמחק", description=f"**נמחק על ידי:** {responsible_user}\n**שם הרול:** `{role.name}`", color=discord.Color.dark_red())
    embed.set_footer(text="Developed by Aharon the gamer")
    if os.path.exists(BACKGROUND_IMAGE): await log_channel.send(file=discord.File(BACKGROUND_IMAGE, filename="background.png"), embed=embed)
    else: await log_channel.send(embed=embed)
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    bot.add_view(RoleRequestStarterView())
    bot.add_view(TicketStarterView())
    if not track_fivem_status.is_running(): track_fivem_status.start()

# 🎯 פקודת ההקמה הרשמית והמחברת של הבוט - המנוע שמדליק הכל 24/7!
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    if TOKEN: 
        bot.run(TOKEN)
