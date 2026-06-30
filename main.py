import os
import json
import asyncio
import logging
from threading import Thread
import aiohttp
from flask import Flask

import discord
from discord.ext import tasks, commands
from discord import app_commands

# --- הגדרות שרת Flask לשמירה על הבוט באוויר (Keep Alive) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    web_app.run(host='0.0.0.0', port=8080)

# --- קבועים והגדרות מערכת ---
FIVEM_IP = "188.66.26.143:30120"
GUILD_ID = 1500997764169863271
BACKGROUND_FILE = "background.png"

# רולים
ROLE_APPROVAL_ID = 1521553580148916325
ROLE_TICKET_STAFF_ID = 1521554756626157788

# חדרים
CH_WELCOME = 1500997767256870922
CH_ROLE_PANEL = 1500997767256870923
CH_ROLE_LOGS = 1521554909021868073
CH_TICKET_PANEL = 1521555870268260423
CH_TICKET_LOGS = 1521557178387795999

# הגדרת הלוגר של הבוט
logging.basicConfig(level=logging.INFO)
class PoliceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.loop_toggle = True

    async def setup_hook(self):
        # רישום ה-Views הקבועים כדי שיעבדו לאחר הפעלה מחדש של הבוט
        self.add_view(RolePanelView())
        self.add_view(TicketPanelView())

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        try:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Successfully synced slash commands.")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        
        if not self.update_fivem_status.is_running():
            self.update_fivem_status.start()

    # --- מערכת ברוכים הבאים ---
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return
        channel = member.guild.get_channel(CH_WELCOME)
        if not channel:
            return

        embed = discord.Embed(
            title="👮‍♂️ ברוך הבא למחלקת המשטרה!",
            description=f"שלום {member.mention},\nשמחים שהצטרפת לשרת הדיסקורד הרשמי של משטרת FiveM!\n\nאנא קרא את החוקים ופנה לפנל הדרגות במידת הצורך.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if os.path.exists(BACKGROUND_FILE):
            bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
            embed.set_image(url="attachment://background.png")
            await channel.send(file=bg_file, embed=embed)
        else:
            await channel.send(embed=embed)
    # --- משימת רקע: סטטוס שרת FiveM ---
    @tasks.loop(seconds=30)
    async def update_fivem_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{FIVEM_IP}/players.json", timeout=5) as players_resp:
                    async with session.get(f"http://{FIVEM_IP}/info.json", timeout=5) as info_resp:
                        if players_resp.status == 200 and info_resp.status == 200:
                            players_data = await players_resp.json()
                            info_data = await info_resp.json()
                            current_players = len(players_data)
                            max_players = info_data.get('vars', {}).get('sv_maxclients', '32')
                            
                            if self.loop_toggle:
                                status_text = f"🟢 Online | {current_players}/{max_players}"
                            else:
                                status_text = f"Watching {current_players}/{max_players} Players"
                        else:
                            status_text = "🔴 Offline"
        except Exception:
            status_text = "🔴 Offline"

        self.loop_toggle = not self.loop_toggle
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_text))

bot = PoliceBot()
# --- מערכת בקשת רולים ודרגות ---
class RoleModal(discord.ui.Modal, title="טופס בקשת רולים ודרגות"):
    staff_name = discord.ui.TextInput(label="שם חבר הצוות שהכניס אותך", placeholder="לדוגמה: ישראל ישראלי", required=True)
    role_details = discord.ui.TextInput(label="פירוט הרולים / הדרגות המבוקשות", style=discord.TextStyle.long, placeholder="פרט כאן את הדרגה שקיבלת ביחידה...", required=True)

    def __init__(self, target_member: discord.Member):
        super().__init__()
        self.target_member = target_member

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("הטופס נשלח בהצלחה לבדיקת ההנהלה המוסמכת.", ephemeral=True)
        
        logs_channel = interaction.guild.get_channel(CH_ROLE_LOGS)
        if not logs_channel:
            return

        embed = discord.Embed(
            title="📋 בקשת דרגה / רול חדשה",
            description=f"**מגיש הבקשה:** {self.target_member.mention} ({self.target_member.id})\n"
                        f"**הוכנס על ידי:** {self.staff_name.value}\n\n"
                        f"**פירוט הדרישה:**\n{self.role_details.value}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=self.target_member.display_avatar.url)
        
        view = RoleApprovalView(target_member_id=self.target_member.id)
        
        if os.path.exists(BACKGROUND_FILE):
            bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
            embed.set_image(url="attachment://background.png")
            await logs_channel.send(file=bg_file, embed=embed, view=view)
        else:
            await logs_channel.send(embed=embed, view=view)

class RolePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="הגשת בקשה לרולים / דרגות", style=discord.ButtonStyle.blurple, custom_id="btn_request_roles", emoji="🎖️")
    async def request_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RoleModal(target_member=interaction.user))
class RoleDropdown(discord.ui.Select):
    def __init__(self, target_member_id: int):
        self.target_member_id = target_member_id
        super().__init__(
            placeholder="בחר רולים להענקה למשתמש...",
            min_values=1,
            max_values=10,
            custom_id=f"select_roles_{target_member_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.get_role(ROLE_APPROVAL_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.target_member_id)
        if not member:
            await interaction.response.send_message("המשתמש לא נמצא בשרת.", ephemeral=True)
            return

        added_roles = []
        for role_id in self.values:
            role = guild.get_role(int(role_id))
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                    added_roles.append(role.name)
                except discord.Forbidden:
                    pass

        roles_str = ", ".join(added_roles) if added_roles else "לא הוענקו רולים חדשים (אולי כבר קיימים או שאין לבוט גישה)"
        await interaction.response.send_message(f"✅ הרולים הבאים הוענקו בהצלחה ל-{member.mention}:\n`{roles_str}`", ephemeral=True)

class RoleApprovalView(discord.ui.View):
    def __init__(self, target_member_id: int):
        super().__init__(timeout=None)
        self.target_member_id = target_member_id
        self.dropdown = RoleDropdown(target_member_id=target_member_id)
        self.add_item(self.dropdown)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        options = []
        for role in reversed(guild.roles):
            if role.is_default() or role.managed:
                continue
            options.append(discord.SelectOption(label=role.name, value=str(role.id)))
            if len(options) == 25:
                break
        self.dropdown.options = options
        return True

    @discord.ui.button(label="סיום פנייה ונתינת רולים", style=discord.ButtonStyle.success, custom_id="btn_finish_role", emoji="✅")
    async def finish_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_APPROVAL_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return
        
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("הפעולה הסתיימה בהצלחה והפנל ננעל.", ephemeral=True)

    @discord.ui.button(label="KICK", style=discord.ButtonStyle.secondary, custom_id="btn_kick_member", emoji="👢")
    async def kick_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_APPROVAL_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return
        
        member = interaction.guild.get_member(self.target_member_id)
        if member:
            try:
                await member.kick(reason="נדחה על ידי פנל ניהול דרגות משטרה")
                await interaction.response.send_message(f"המשתמש {member.name} הועף מהשרת (Kick).", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("אין לבוט הרשאות להעיף משתמש זה.", ephemeral=True)
        else:
            await interaction.response.send_message("המשתמש לא נמצא בשרת.", ephemeral=True)

    @discord.ui.button(label="BAN", style=discord.ButtonStyle.danger, custom_id="btn_ban_member", emoji="🔨")
    async def ban_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_APPROVAL_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return

        member = interaction.guild.get_member(self.target_member_id)
        if member:
            try:
                await member.ban(reason="נדחה ונחסם על ידי פנל ניהול דרגות משטרה")
                await interaction.response.send_message(f"המשתמש {member.name} נחסם מהשרת (Ban).", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("אין לבוט הרשאות לחסום משתמש זה.", ephemeral=True)
        else:
            await interaction.response.send_message("המשתמש לא נמצא בשרת.", ephemeral=True)
# --- מערכת טיקטים (פניות צוות) ---
class AddUserModal(discord.ui.Modal, title="הוספת משתמש לטיקט"):
    user_id = discord.ui.TextInput(label="מזהה המשתמש (ID) או תיוג", placeholder="הכנס מזהה משתמש כאן...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        clean_id = self.user_id.value.replace("<@", "").replace(">", "").strip()
        try:
            member = interaction.guild.get_member(int(clean_id))
            if member:
                await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
                await interaction.response.send_message(f"המשתמש {member.mention} נוסף בהצלחה לטיקט.", ephemeral=False)
            else:
                await interaction.response.send_message("משתמש זה לא נמצא בשרת.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("מזהה משתמש לא תקין.", ephemeral=True)

class RenameTicketModal(discord.ui.Modal, title="שינוי שם חדר הטיקט"):
    new_name = discord.ui.TextInput(label="שם החדר החדש", placeholder="לדוגמה: טיפול-בבאג", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=self.new_name.value)
        await interaction.response.send_message(f"שם החדר שונה בהצלחה ל: `{self.new_name.value}`", ephemeral=True)

class CloseTicketModal(discord.ui.Modal, title="סגירת טיקט - לוג מסכם"):
    summary = discord.ui.TextInput(label="סיכום הטיפול בפנייה", style=discord.TextStyle.long, required=True)
    resolved = discord.ui.TextInput(label="האם קיבל מענה מלא? (כן/לא)", max_length=5, required=True)

    def __init__(self, ticket_owner_id: int, ticket_type: str, claimed_by_id: int):
        super().__init__()
        self.ticket_owner_id = ticket_owner_id
        self.ticket_type = ticket_type
        self.claimed_by_id = claimed_by_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("הטיקט נסגר, החדר יימחק מיד...", ephemeral=True)
        
        log_channel = interaction.guild.get_channel(CH_TICKET_LOGS)
        if log_channel:
            owner = interaction.guild.get_member(self.ticket_owner_id)
            staff = interaction.guild.get_member(self.claimed_by_id)
            
            owner_text = owner.mention if owner else f"עזב את השרת ({self.ticket_owner_id})"
            staff_text = staff.mention if staff else "לא נלקח על ידי איש צוות מסוים"

            embed = discord.Embed(
                title="🔒 לוג סגירת טיקט",
                description=f"**סוג הפנייה:** {self.ticket_type}\n"
                            f"**פתח את הטיקט:** {owner_text}\n"
                            f"**טופל על ידי:** {staff_text}\n"
                            f"**נסגר על ידי:** {interaction.user.mention}\n\n"
                            f"**האם קיבל מענה מלא:** {self.resolved.value}\n"
                            f"**סיכום טיפול:**\n{self.summary.value}",
                color=discord.Color.red()
            )
            
            if os.path.exists(BACKGROUND_FILE):
                bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
                embed.set_image(url="attachment://background.png")
                await log_channel.send(file=bg_file, embed=embed)
            else:
                await log_channel.send(embed=embed)
                
        await asyncio.sleep(2)
        await interaction.channel.delete()
class InsideTicketView(discord.ui.View):
    def __init__(self, owner_id: int, ticket_type: str):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.ticket_type = ticket_type
        self.claimed_by = None

    @discord.ui.button(label="לקיחת הפנייה", style=discord.ButtonStyle.success, custom_id="btn_claim_ticket", emoji="🙋‍♂️")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_TICKET_STAFF_ID):
            await interaction.response.send_message("רק צוות הטיקטים מורשה ללחוץ על כפתור זה.", ephemeral=True)
            return
        
        if self.claimed_by is not None:
            await interaction.response.send_message("פנייה זו כבר נלקחה על ידי איש צוות אחר.", ephemeral=True)
            return

        self.claimed_by = interaction.user.id
        button.disabled = True
        button.label = f"נלקח ע''י {interaction.user.display_name}"
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"איש הצוות {interaction.user.mention} לקח על עצמו את הטיפול בפנייה זו.", ephemeral=False)

    @discord.ui.button(label="שינוי שם חדר", style=discord.ButtonStyle.primary, custom_id="btn_rename_ticket", emoji="✏️")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_TICKET_STAFF_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return
        await interaction.response.send_modal(RenameTicketModal())

    @discord.ui.button(label="הוספת משתמש", style=discord.ButtonStyle.secondary, custom_id="btn_add_user_ticket", emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_TICKET_STAFF_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="סגירת הפנייה", style=discord.ButtonStyle.danger, custom_id="btn_close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ROLE_TICKET_STAFF_ID):
            await interaction.response.send_message("אין לך הרשאה לבצע פעולה זו.", ephemeral=True)
            return
        
        claimed_id = self.claimed_by if self.claimed_by else interaction.user.id
        await interaction.response.send_modal(CloseTicketModal(ticket_owner_id=self.owner_id, ticket_type=self.ticket_type, claimed_by_id=claimed_id))

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="שאלה כללית", value="שאלה כללית", emoji="❓"),
            discord.SelectOption(label="דיווח באג", value="דיווח באג", emoji="🐛"),
            discord.SelectOption(label="תלונה על שוטר", value="תלונה על שוטר", emoji="👮‍♂️"),
            discord.SelectOption(label="אחר", value="אחר", emoji="📁")
        ]
        super().__init__(placeholder="בחר את נושא הפנייה לפתיחת טיקט...", min_values=1, max_values=1, options=options, custom_id="dropdown_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        staff_role = guild.get_role(ROLE_TICKET_STAFF_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        
        await interaction.response.send_message(f"נפתח עבורך חדר פנייה חדש: {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"🎫 פנייה חדשה בנושא: {ticket_type}",
            description=f"שלום {user.mention},\nצוות הטיקטים קיבל את פנייתך. אנא פרט כאן את הבעיה שלך בצורה המלאה ביותר, ואיש צוות יתפנה אליך בהקדם האפשרי.",
            color=discord.Color.blue()
        )
        
        view = InsideTicketView(owner_id=user.id, ticket_type=ticket_type)
        
        if os.path.exists(BACKGROUND_FILE):
            bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
            embed.set_image(url="attachment://background.png")
            await ticket_channel.send(file=bg_file, embed=embed, view=view)
        else:
            await ticket_channel.send(embed=embed, view=view)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())
# --- פקודות Setup (סלאש רשמיות בלבד) ---
@bot.tree.command(name="setup_role_panel", description="יוצר ומציב את פנל בקשת הרולים והדרגות")
async def setup_role_panel(interaction: discord.Interaction):
    if interaction.channel_id != CH_ROLE_PANEL:
        await interaction.response.send_message(f"ניתן להריץ פקודה זו רק בחדר המיועד לכך.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎖️ מערכת דרגות ורולים דיגיטלית",
        description="ברוכים הבאים לפנל קבלת הדרגות של מחלקת המשטרה.\n\n"
                    "במידה והוכנסתם ליחידה מסוימת או קודמתם בדרגה על ידי דרג פיקודי, לחצו על הכפתור מטה ומלאו את הטופס.",
        color=discord.Color.blue()
    )
    
    if os.path.exists(BACKGROUND_FILE):
        bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        await interaction.response.send_message("מציב את הפנל...", ephemeral=True)
        await interaction.channel.send(file=bg_file, embed=embed, view=RolePanelView())
    else:
        await interaction.response.send_message(embed=embed, view=RolePanelView())

@bot.tree.command(name="setup_ticket_panel", description="יוצר ומציב את פנל פתיחת הטיקטים")
async def setup_ticket_panel(interaction: discord.Interaction):
    if interaction.channel_id != CH_TICKET_PANEL:
        await interaction.response.send_message(f"ניתן להריץ פקודה זו רק בחדר המיועד לכך.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 מרכז תמיכה ופניות - משטרת FiveM",
        description="זקוק לעזרה? נתקלת בבעיה כלשהי או ברצונך להגיש תלונה?\n\n"
                    "בחר את הקטגוריה המתאימה ביותר מהתפריט הנגלל למטה כדי לפתוח חדר דיון פרטי מול חברי הצוות.",
        color=discord.Color.blue()
    )
    
    if os.path.exists(BACKGROUND_FILE):
        bg_file = discord.File(BACKGROUND_FILE, filename="background.png")
        embed.set_image(url="attachment://background.png")
        await interaction.response.send_message("מציב את הפנל...", ephemeral=True)
        await interaction.channel.send(file=bg_file, embed=embed, view=TicketPanelView())
    else:
        await interaction.response.send_message(embed=embed, view=TicketPanelView())

# --- הפעלת הבוט המשולב עם Flask לטובת Keep-Alive 24/7 ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    BOT_TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
    if BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        bot.run(BOT_TOKEN)
    else:
        print("Please set your DISCORD_TOKEN configuration.")
