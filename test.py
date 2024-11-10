import discord
import json
import requests
from discord.ext import commands
import colorama 
from colorama import Fore, Style

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

with open('countries.json', 'r') as file:
    countries = json.load(file)

with open('services.json', 'r') as file:
    services = json.load(file)

intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix='.', intents=intents)
TOKEN = config['token']
api = config['api_key']
ref = config['ref_id']
authorized_members = config['authorized_members']
id = None
number = None



def is_authorized(ctx):
    return ctx.author.id in authorized_members

async def check_balance():
    balance_url = f"https://api.tiger-sms.com/stubs/handler_api.php?api_key={api}&action=getBalance"
    response = requests.get(balance_url)
    balance = response.text.split(":")[1].strip()  
    balance_value = float(balance)
    if 'BAD_KEY' in response.text:
        return "❌ Invalid API Key"
    return f" 💸 Balance: `{balance_value}` ₽ "

async def get_number_for_service_and_country(service_name, country_name):
    global id, number
    country_name = country_name.lower()
    service_name = service_name.lower()
    if country_name not in countries:
        return "Country not found."
    if service_name not in services:
        return "Service not found."
    country = countries[country_name]
    service = services[service_name]
    url = f'https://api.tiger-sms.com/stubs/handler_api.php?api_key={api}&action=getNumber&service={service}&country={country}&ref={ref}'
    response = requests.get(url)
    try:
        parts = response.text.split(":")
        if len(parts) < 3:
            return f"❌ Error: Unexpected API response - {response.text}"
        id = parts[1]
        number = parts[2]
        return f":shopping_cart: Purchased Number : {number}\n :white_check_mark: Country : {country}\n:rocket: Activation ID : {id}"
    except Exception as e:
        return f"⌛ Error parsing API response: {str(e)}"

async def get_price_for_service_and_country(service_name, country_name):
    country_name = country_name.lower()
    service_name = service_name.lower()
    if country_name not in countries:
        return "🚫Country not found."
    if service_name not in services:
        return "🚫Service not found."
    country = countries[country_name]
    service = services[service_name]
    global presponse
    price_url = f'https://api.tiger-sms.com/stubs/handler_api.php?api_key={api}&action=getPrices&service={service}&country={country}'
    presponse = requests.get(price_url)
    if presponse.text.startswith("ERROR"):
        return "❌  Error fetching price data. Please try again later."
    try:
        price_data = presponse.json()
        price = price_data.get(f"{service}", {}).get(f"{country}")
        if price:
            return f"Price for service '{service_name}' in country '{country_name}': {price} units"
        else:
            return f"🚫 Price data not available for service '{service_name}' in country '{country_name}'."
    except ValueError:
        return f"🚫 Unexpected response format: {presponse.text}"

async def get_otp():
    if not id:
        return "No ID found, please run .buy first."
    code_url = f"https://api.tiger-sms.com/stubs/handler_api.php?api_key={api}&action=getStatus&id={id}"
    get_code = requests.get(url=code_url)
    return f"OTP request response: {get_code.text}"

class NumberButtonView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_button")
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global id, number
        id = None
        number = None
        await interaction.response.send_message(" ❌ Operation canceled. You May Fetch New Number ", ephemeral=True)

    @discord.ui.button(label="⚡ OTP", style=discord.ButtonStyle.success, custom_id="otp_button")
    async def otp_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("⌛ Sending OTP request...", ephemeral=True)
        result = await get_otp()
        await interaction.followup.send(result)

    @discord.ui.button(label="Copy Number", style=discord.ButtonStyle.primary, custom_id="copy_button")
    async def copy_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if number:
            await interaction.response.send_message(f"{number}")
        else:
            await interaction.response.send_message(" 🚫 No number found. Please run `.buy` first.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{Fore.LIGHTMAGENTA_EX}We have logged in as {bot.user}{Style.RESET_ALL}')

@bot.command()
async def balance(ctx):
    if not is_authorized(ctx):
        await ctx.send("🚫 You are not authorized to use this command.")
        return
    balance_message = await check_balance()
    await ctx.send(balance_message)

@bot.command()
async def bal(ctx):
    if not is_authorized(ctx):
        await ctx.send("🚫 You are not authorized to use this command.")
        return
    balance_message = await check_balance()
    await ctx.send(balance_message)

@bot.command()
async def otp(ctx):
    if not is_authorized(ctx):
        await ctx.send("🚫 You are not authorized to use this command.")
        return
    result = await get_otp()
    await ctx.send(result)

@bot.command()
async def buy(ctx, service_name: str, country_name: str):
    if not is_authorized(ctx):
        await ctx.send("🚫 You are not authorized to use this command.")
        return
    global id, number
    await ctx.send(f":mag_right: Fetching Number For : {service_name} \nCountry: {country_name}")
    result = await get_number_for_service_and_country(service_name, country_name)
    if "Purchased Number" in result:
        await ctx.send(result, view=NumberButtonView())
    else:
        await ctx.send(result)

@bot.command()
async def price(ctx, service_name: str, country_name: str):
    if not is_authorized(ctx):
        await ctx.send("🚫 You are not authorized to use this command.")
        return
    await ctx.send(f"🔍 Fetching Prices : {service_name} \n Country : {country_name}")
    result = await get_price_for_service_and_country(service_name, country_name)
    await ctx.send(f":green_circle: Found Results \n {presponse.text}")

bot.run(TOKEN)
