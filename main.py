import discord
import requests
import datetime
import os
import asyncio
import random
import openai
import yfinance as yf
from discord.ext import tasks
from dotenv import load_dotenv


# .env fájl betöltése
load_dotenv()

# Discord bot token
TOKEN = os.getenv('TOKEN')

#_______________________________________________________________________________________________

# Twelve Data API kulcsok
KEY_1 = os.getenv('KEY_1')
KEY_2 = os.getenv('KEY_2')
KEY_3 = os.getenv('KEY_3')
KEY_4 = os.getenv('KEY_4')
KEY_5 = os.getenv('KEY_5')
KEY_6 = os.getenv('KEY_6')
KEY_7 = os.getenv('KEY_7')
KEY_8 = os.getenv('KEY_8')
KEY_9 = os.getenv('KEY_9')
KEY_10 = os.getenv('KEY_10')
KEY_11 = os.getenv('KEY_11')
KEY_12 = os.getenv('KEY_12')


#_______________________________________________________________________________________________

# Financial Modeling Prep API kulcs
FMP_API_KEY = os.getenv('FMP_API_KEY')

# Engedélyezett szerver ID
ALLOWED_GUILD_ID = int(os.getenv('ALLOWED_GUILD_ID'))

# Bot inicializálása
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

#_______________________________________________________________________________________________


# Diagram URL-ek
def get_chart_urls(symbol):
    base_url = 'https://charts2-node.finviz.com/chart.ashx'
    
    return {
        'weekly':
        f'{base_url}?cs=l&t={symbol}&tf=w&s=linear&ct=candle_stick&o[0][ot]=sma&o[0][op]=20&o[0][oc]=FF8F33C6&o[1][ot]=sma&o[1][op]=50&o[1][oc]=DCB3326D&o[2][ot]=sma&o[2][op]=200&o[2][oc]=DC32B363&o[3][ot]=patterns&o[3][op]=&o[3][oc]=000',
        'daily':
        f'{base_url}?cs=l&t={symbol}&tf=d&s=linear&ct=candle_stick&o[3][ot]=patterns&o[3][op]=&o[3][oc]=000',
        '3d':
        f'https://api.wsj.net/api/kaavio/charts/big.chart?nosettings=1&symb={symbol}&type=4&time=3&freq=6&style=330&lf=6&lf2=0&lf3=0&size=2&height=335&width=579&mocktick=1&rr=1726150438577'
    }


# Árak lekérése
def get_stock_prices(symbol, key):
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    one_month_ago = today - datetime.timedelta(days=30)
    one_day_ago = today - datetime.timedelta(days=1)

    one_year_ago_str = one_year_ago.strftime('%Y-%m-%d')
    one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
    one_day_ago_str = one_day_ago.strftime('%Y-%m-%d')

    url_now = f'https://api.twelvedata.com/price?symbol={symbol}&apikey={key}'
    url_past = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&start_date=2023-01-01&apikey={key}'

    try:
        # Fetch current price
        response_now = requests.get(url_now).json()
        price_now = float(response_now.get('price', 'N/A'))

        # Fetch past prices
        response_past = requests.get(url_past).json()

        values = response_past.get('values', [])

        if isinstance(values, list):
            # Create a dictionary for fast lookups
            values_dict = {
                entry['datetime']: float(entry['close'])
                for entry in values
            }

            # Get prices for the desired dates, default to 'N/A' if not found
            price_day_ago = values_dict.get(one_day_ago_str, 'N/A')
            price_month_ago = values_dict.get(one_month_ago_str, 'N/A')
            price_year_ago = values_dict.get(one_year_ago_str, 'N/A')
        else:
            price_day_ago = 'N/A'
            price_month_ago = 'N/A'
            price_year_ago = 'N/A'

        # Calculate percentage change
        def format_change(current, previous):
            if previous == 0 or previous == 'N/A':
                return "+0.00%"

            try:
                change = current - previous
                percentage_change = (change / previous) * 100
                return f"{percentage_change:.2f}%" if percentage_change >= 0 else f"{percentage_change:.2f}%"
            except (TypeError, ValueError):
                return "N/A"

        return {
            'price_now':
            round(price_now, 2) if isinstance(price_now, float) else 'N/A',
            'price_day_ago':
            round(price_day_ago, 2)
            if isinstance(price_day_ago, float) else 'N/A',
            'price_month_ago':
            round(price_month_ago, 2)
            if isinstance(price_month_ago, float) else 'N/A',
            'price_year_ago':
            round(price_year_ago, 2)
            if isinstance(price_year_ago, float) else 'N/A',
            'change_day':
            format_change(price_now, price_day_ago),
            'change_month':
            format_change(price_now, price_month_ago),
            'change_year':
            format_change(price_now, price_year_ago)
        }

    except requests.RequestException as e:
        return {'error': f'Error fetching data: {e}'}


#_______________________________________________________________________________________________


# Üzenetek törlése a csatornán
async def delete_messages_7(channel):
    async for message in channel.history(limit=7):
        if message.author == channel.guild.me:  # Check if the author is the bot itself
            try:
                await message.delete()
                await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = int(e.response.headers.get('Retry-After',
                                                             1)) / 1000
                    print(
                        f"Rate limit hit. Retrying after {retry_after} seconds."
                    )
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    print(f"Failed to delete message: {e}")


#_______________________________________________________________________________________________


# Árak és diagram frissítése
async def update_channel_prices(symbol, key, channel_name):
    guild = discord.utils.get(client.guilds, id=ALLOWED_GUILD_ID)
    if guild is not None:
        channel = discord.utils.get(guild.text_channels, name=channel_name)

        if channel is not None:
            # Üzenetek törlése
            await delete_messages_7(channel)

            # Árak és diagramok frissítése
            prices = get_stock_prices(symbol, key)
            urls = get_chart_urls(symbol)

            if 'error' in prices:
                print(prices['error'])
                return

            # Képek és árak üzenetekben
            embed = discord.Embed(title=f"{symbol} Prices",
                                  color=discord.Color.green())
            embed.add_field(name="Current",
                            value=f"${prices['price_now']}",
                            inline=False)
            embed.add_field(
                name="1 Day Ago",
                value=f"${prices['price_day_ago']} ({prices['change_day']})",
                inline=False)
            embed.add_field(
                name="1 Month Ago",
                value=
                f"${prices['price_month_ago']} ({prices['change_month']})",
                inline=False)
            embed.add_field(
                name="1 Year Ago",
                value=f"${prices['price_year_ago']} ({prices['change_year']})",
                inline=False)

            # Árak üzenet elküldése
            try:
                await channel.send(embed=embed)
                await asyncio.sleep(0.5)
                await channel.send("Weekly Chart")
                await asyncio.sleep(0.5)
                await channel.send(urls['weekly'])
                await asyncio.sleep(0.5)
                await channel.send("Daily Chart:")
                await asyncio.sleep(0.5)
                await channel.send(urls['daily'])
                await asyncio.sleep(0.5)
                await channel.send("3 day chart:")
                await asyncio.sleep(0.5)
                await channel.send(urls['3d'])
                await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = int(e.response.headers.get('Retry-After',
                                                             1)) / 1000
                    print(
                        f"Rate limit hit. Retrying after {retry_after} seconds."
                    )
                    await asyncio.sleep(retry_after)
                    await update_channel_prices(symbol, key, channel_name)

        else:
            print(f"Channel {channel_name} not found.")
    else:
        print("Guild not found.")


#_______________________________________________________________________________________________


# Legnagyobb vesztesek lekérése
def get_top_losers():
    url = f'https://financialmodelingprep.com/api/v3/stock/losers?apikey={FMP_API_KEY}'
    try:
        response = requests.get(url).json()
        if isinstance(response, dict) and 'mostLoserStock' in response:
            return response['mostLoserStock']
        else:
            print('Unexpected response format:', response)
            return []
    except requests.RequestException as e:
        print(f'Error fetching data: {e}')
        return []


# Legnagyobb nyertesek lekérése
def get_top_gainers():
    url = f'https://financialmodelingprep.com/api/v3/stock/gainers?apikey={FMP_API_KEY}'
    try:
        response = requests.get(url).json()
        if isinstance(response, dict) and 'mostGainerStock' in response:
            return response['mostGainerStock']
        else:
            print('Unexpected response format:', response)
            return []
    except requests.RequestException as e:
        print(f'Error fetching data: {e}')
        return []


#_______________________________________________________________________________________________


# Top vesztesek frissítése
async def update_channel_losers():
    guild = discord.utils.get(client.guilds, id=ALLOWED_GUILD_ID)
    if guild is not None:
        channel = discord.utils.get(guild.text_channels,
                                    name='top-stock-losers')

        if channel is not None:
            # Üzenetek törlése
            await delete_messages_7(channel)

            # Legnagyobb vesztesek lekérése
            losers = get_top_losers()

            # Top gainer link küldése
            await channel.send(
                "Top gainers in 1 month: https://shorturl.at/bE6Bw")

            if losers:
                # Embed készítése
                embed = discord.Embed(title="Top 10 Stock Losers Today",
                                      color=discord.Color.red())

                if isinstance(losers, list):
                    for i, loser in enumerate(
                            losers[49:39:-1]):  # Az első 10 legnagyobb vesztes
                        name = loser.get('companyName', 'N/A')
                        symbol = loser.get('ticker', 'N/A')
                        percent_loss = loser.get('changesPercentage', '0.00')
                        try:
                            percent_loss_float = float(percent_loss.strip('%'))
                            percent_loss_display = f"{percent_loss_float:.2f}%"
                        except ValueError:
                            percent_loss_display = percent_loss

                        embed.add_field(
                            name=f"{i+1}. {name} ({symbol})",
                            value=f"Change: {percent_loss_display}",
                            inline=False)
                else:
                    embed.add_field(name="Error",
                                    value="Invalid data format received",
                                    inline=False)

                # Üzenet küldése
                await channel.send(embed=embed)
            else:
                await channel.send("No data available for today.")

        else:
            print("Channel 'top-stock-losers' not found.")
    else:
        print("Guild not found.")


# Top növekedők frissítése
async def update_channel_gainers():
    guild = discord.utils.get(client.guilds, id=ALLOWED_GUILD_ID)
    if guild is not None:
        channel = discord.utils.get(guild.text_channels,
                                    name='top-stock-gainers')

        if channel is not None:
            # Üzenetek törlése
            await delete_messages_7(channel)

            # Legnagyobb növekedők lekérése
            gainers = get_top_gainers()

            # Top gainer link küldése
            await channel.send(
                "Top gainers in 1 month: https://shorturl.at/bV4L1")

            if gainers:
                # Embed készítése
                embed = discord.Embed(title="Top 10 Stock Gainers Today",
                                      color=discord.Color.green())

                if isinstance(gainers, list):
                    for i, gainer in enumerate(gainers[:10]):
                        name = gainer.get('companyName', 'N/A')
                        symbol = gainer.get('ticker', 'N/A')
                        percent_gain = gainer.get('changesPercentage', '0.00')
                        try:
                            percent_gain_float = float(percent_gain.strip('%'))
                            percent_gain_display = f"{percent_gain_float:.2f}%"
                        except ValueError:
                            percent_gain_display = percent_gain

                        embed.add_field(
                            name=f"{i+1}. {name} ({symbol})",
                            value=f"Change: {percent_gain_display}",
                            inline=False)
                else:
                    embed.add_field(name="Error",
                                    value="Invalid data format received",
                                    inline=False)

                # Üzenet küldése
                await channel.send(embed=embed)
            else:
                await channel.send("No data available for today.")

        else:
            print("Channel 'top-stock-gainers' not found.")
    else:
        print("Guild not found.")


#_______________________________________________________________________________________________

#_______________________________________________________________________________________________


# Periodikus frissítések beállítása
@tasks.loop(minutes=30)
async def periodic_update_losers():
    await update_channel_losers()


@tasks.loop(minutes=30)
async def periodic_update_gainers():
    await update_channel_gainers()


#_______________________________________________________________________________________________


@tasks.loop(minutes=5)
async def periodic_update_prices():
    await update_channel_prices('QQQ', KEY_1, 'qqq')
    await asyncio.sleep(1)
    await update_channel_prices('AAPL', KEY_11, 'aapl')
    await asyncio.sleep(1)
    await update_channel_prices('NVDA', KEY_2, 'nvda')
    await asyncio.sleep(1)
    await update_channel_prices('TSLA', KEY_3, 'tsla')
    await asyncio.sleep(1)
    await update_channel_prices('PLTR', KEY_4, 'pltr')
    await asyncio.sleep(1)
    await update_channel_prices('NOW', KEY_5, 'now')
    await asyncio.sleep(1)
    await update_channel_prices('MSFT', KEY_6, 'msft')
    await asyncio.sleep(1)
    await update_channel_prices('IYW', KEY_7, 'iyw')
    await asyncio.sleep(1)
    await update_channel_prices('SPXL', KEY_8, 'spxl')
    await asyncio.sleep(1)
    await update_channel_prices('GLD', KEY_9, 'gld')
    await update_channel_prices('TQQQ', KEY_10, 'tqqq')
    await asyncio.sleep(1)
    await asyncio.sleep(1)
    await update_channel_prices('SPY', KEY_10, 'spy')
    await asyncio.sleep(1)


#_______________________________________________________________________________________________
technology = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "IBM", "ORCL",
        "CSCO", "INTC", "AMD", "ADBE", "PYPL", "SQ", "CRM", "SHOP", "SNOW",
        "ZM", "TWTR", "BA", "T", "V", "MA", "HD", "DIS", "NFLX", "PFE", "MRNA",
        "RBLX", "UBER", "LYFT", "FSLY", "NOW", "BABA", "JD", "NTDOY", "NXPI",
        "QCOM", "TXN", "AVGO", "STX", "WDC", "MU", "AMAT", "LRCX", "KLAC",
        "HPE", "DELL", "MSI", "HUBS", "RNG", "ZS", "PANW", "NET", "DOCU",
        "SMAR", "SPLK", "TTD", "PSTG", "TENB", "PLTR", "SE", "BIDU", "TME",
        "DIDI", "HIMX", "AEYE", "FLIR", "CRWD", "CLDR", "GILD", "ANET", "PDD",
        "NLOK", "VRSN", "EOLS", "INSG", "TRMB", "MCHP", "CIEN", "GTNX", "MU",
        "NVDA", "CSX", "HPE", "ENPH", "SNY", "RMD", "DTEGY", "MAR", "STNE",
        "PDD", "EDU", "BIDU", "MCHP", "DLO", "SHOP", "TTD", "DTRM", "COIN",
        "DT", "TRUP", "TTC", "CYBR", "TMO", "GDDY", "RNG", "WDC", "PGR",
        "MRVL", "CRWD", "FTNT", "RDFN", "DKNG", "Z", "DOCU", "NLOK", "VMW",
        "AAPL", "MSFT", "GOOG", "AMZN", "META", "ORCL", "V", "MA", "NFLX",
        "BA", "XOM", "MCD", "CVX", "WMT", "KO", "PEP", "COST", "TMO", "NKE",
        "UNP", "ABT", "MCK", "MDT", "AMGN", "BMY", "GILD", "VZ", "T", "WBA",
        "DHR", "AON", "D", "ETN", "LMT", "JPM", "BAC", "USB", "GS", "MS",
        "STT", "C", "AXP", "MA", "V", "PYPL", "SO", "EIX", "XEL", "CMS",
        "WEC", "DTE", "WTRG", "AWK", "NWE", "ES", "EXC", "NI", "PEG", "SRE",
        "TRP", "ENB", "PPL", "CNP", "SRE", "LNT", "AEE", "ED", "DU", "XOM",
        "CVX", "EOG", "HES", "PXD", "MRO", "FANG", "LNG", "WMB", "OKE",
        "PXD", "TMO", "UNH", "CNC", "HCA", "DVA", "AET", "CVS", "CI", "ANTM",
        "WLTW", "HUM", "BAX"
    ]

healthcare = [
        "JNJ", "PFE", "MRK", "ABBV", "AMGN", "GILD", "BMY", "MDT", "ABT", "LLY",
        "CVS", "UNH", "HUM", "DVA", "CI", "ANTM", "CNC", "WCG", "HCA", "ESPR",
        "VEEV", "ISRG", "SYK", "BSX", "RMD", "BDX", "COO", "ZBH", "TMO", "ILMN",
        "VRTX", "REGN", "ALXN", "NVS", "SNY", "BAX", "SAGE", "NVO", "PODD", "HRTX",
        "BMRN", "PTCT", "TNDM", "XLRN", "AMGN", "DHR", "HOLX", "JAZZ", "AZN", "MDGL",
        "PRGO", "CVM", "ZTS", "GSK", "UHS", "HCA", "HAD", "MYL", "STJ", "INCY",
        "MCK", "GILD", "IDXX", "CVS", "GILD", "AGN", "NGEN", "A", "UCB", "BMRN",
        "GILD", "PFE", "MRNA", "AUPH", "PRAH", "LIVN", "STADA", "EBS", "BPMC", "TCBI",
        "CBAY", "AMED", "DNDN", "KURA", "NKTR", "LAD", "GSK", "QGEN", "MDGS", "HDSN",
        "CLVS", "BMRN", "GHDX", "TTOO", "LOXO", "BIVV", "OPK", "BMY", "OPGN", "HRC",
        "NTLA", "GTX", "TGTX", "RPTX", "AFMD", "SNY", "OHS", "COLL", "EBS", "AVRO",
        "DMTK", "CPRX", "CEMI", "RPTX", "IVAC", "XOMA", "ARVN", "SAGE", "NVTA", "NVS",
        "SRPT", "RPTX", "NTRA", "CLVS", "ALNY", "BPMC", "RLMD", "VIR", "ABMD", "STML",
        "INFI", "APYX", "PTGX", "ALLO", "MREO", "OTIC", "SYN", "BCYC", "PROG", "OTIC",
        "AMAG", "MTEM", "TCDA", "CVRX", "RTTR", "CRIS", "EBS", "PHIO", "NVCN", "APTX",
        "AXSM", "JAZZ", "KRTX", "IMTX", "DMTX", "AVGR", "GTHX", "EGAN", "BLCM", "PIRS",
        "BLU", "PRTS", "HGEN", "PRGO", "WVE", "MDGL", "TIL", "ADRO", "SYN", "KNTE"
    ]

financials = [
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "TFC", "PNC", "COF",
    "AXP", "MA", "V", "BRK.B", "BLK", "MSCI", "SCHW", "STT", "NTRS", "BK",
    "AIG", "MET", "PRU", "LNC", "PFG", "SIVB", "CME", "ICE", "CBOE", "BAX",
    "HIG", "MTB", "CFG", "NDAQ", "FITB", "RJF", "RBC", "WAL", "TRV", "MFC",
    "SLF", "LPLA", "OFG", "BMO", "ZION", "FRC", "TROW", "KMX", "HSBC", "UBS",
    "BBVA", "RBS", "NAB", "ANZ", "SBSW", "AON", "AFL", "ALL", "L", "TRV",
    "BNS", "RBC", "HSBC", "HDFC", "ICICI", "KOTAK", "SBI", "YES", "IDFC", "OBC",
    "FED", "SYN", "UCO", "DENA", "INDO", "VIB", "UBI", "PUN", "CAN", "INDUS",
    "HDFC", "ICICI", "BANK", "SBI", "PNB", "BOI", "UCO", "UBI", "CEN", "CORP",
    "SYN", "DEN", "OBC", "FED", "SYN", "IDFC", "YES", "BAND", "LAX", "SIB",
    "KAR", "LV", "CUB", "BAM", "CM", "IIFL", "DB", "WFC", "GS", "HIG",
    "TROW", "SCHW", "SIVB", "BK", "BBT", "WFC", "FITB", "KEY", "PNC", "MST",
    "MCO", "SPGI", "LPLA", "VOYA", "PRU", "PFG", "CME", "ICE", "NDAQ",
    "FICO", "AON", "BAX", "CBOE", "CME", "GPN", "FIS", "PAYX", "ADP", "WEX",
    "FISV", "RHI", "EFX", "GPN", "FIS", "MA", "V", "ACGL", "MKTX", "BRK.B",
    "DOV", "RE", "CMA", "EIX", "GIB", "JPM", "BAC", "C", "GS", "MS",
    "STT", "BMO", "MSCI", "NTRS", "V", "MA", "BK", "USB", "TFC", "PNC"
]

consumer_discretionary = [
    "AMZN", "TSLA", "MCD", "DIS", "NKE", "HD", "LOW", "CMG", "SBUX", "BKNG",
    "TGT", "WMT", "KSS", "ULTA", "LULU", "TIF", "PVH", "KMX", "FL", "DECK",
    "YUM", "DHI", "LEN", "RCL", "NCLH", "CCL", "RCL", "HBI", "GPC", "ETSY",
    "LVS", "WYNN", "MGM", "CZR", "HBI", "HAS", "ROST", "TJX", "ANF", "GPS",
    "WBA", "CVS", "MDLZ", "COST", "BURL", "FIVE", "HVT", "PBI", "GME", "BBY",
    "DREY", "ROST", "ALGN", "NKE", "BABA", "PDD", "JD", "LVMUY", "COTY", "MULE",
    "TAP", "ABEV", "CAG", "GIS", "SJM", "HSY", "K", "JJSF", "MDP", "CPB",
    "PEP", "KO", "CAG", "SYY", "ADM", "SJM", "MDLZ", "WBA", "CVS", "HUM",
    "MCK", "ABT", "LLY", "NVO", "BMY", "AZN", "GILD", "PFE", "MRK", "AMGN",
    "BAX", "FDC", "BIIB", "REGN", "CELG", "VRTX", "NVS", "LLY", "ISRG", "ZTS",
    "TDY", "IQV", "RGEN", "ADPT", "NTRA", "WAT", "BCR", "GILD", "SYNH", "HCA",
    "UHS", "THC", "ALXN", "MYL", "WELL", "SJM", "CAG", "POM", "VTR", "BXP",
    "REXR", "CUBE", "NLY", "CLP", "VNO", "STOR", "MFA", "DLR", "SLG", "IRM",
    "SPG", "O", "AVB", "ESS", "MAA", "EQR", "ARE", "OHI", "HCP", "WPC",
    "VICI", "BPY", "BXP", "WELL", "DRE", "DUO", "JPM", "BAC", "GS", "MS",
    "C", "WFC", "STT", "PNC", "USB", "TFC", "FITB", "COF", "JPM", "BAC",
    "C", "GS", "MS", "WFC", "PNC", "USB", "TFC", "FITB", "COF", "JPM",
    "BAC", "C", "GS", "MS", "WFC", "PNC", "USB", "TFC", "FITB", "COF",
    "JPM", "BAC", "C", "GS", "MS", "WFC", "PNC", "USB", "TFC", "FITB",
    "COF", "JPM", "BAC", "C", "GS", "MS", "WFC", "PNC", "USB", "TFC",
    "FITB", "COF", "JPM", "BAC", "C", "GS", "MS", "WFC", "PNC", "USB",
    "TFC", "FITB", "COF"
]

energy = [
    "XOM", "CVX", "COP", "EOG", "PXD", "OXY", "SLB", "HAL", "WMB", "KMI",
    "ET", "MRO", "HES", "PSX", "VLO", "BKR", "DVN", "APA", "NBL", "FTI",
    "TRP", "ENB", "SU", "MPC", "CQP", "GOLD", "TOT", "BP", "RDS.A", "RDS.B",
    "EIA", "E", "PPL", "CVE", "PXD", "FANG", "EQT", "NOG", "CPE", "KOS",
    "WLL", "SD", "MUR", "NOG", "GTE", "GOLD", "TTE", "KMI", "HES", "XOM",
    "CVX", "NEM", "RRC", "EIA", "CVE", "PBR", "KOG", "NBL", "DNR", "PXD",
    "MUR", "XOM", "NBL", "HES", "BCEI", "CLR", "NOG", "CDEV", "MUR", "SM",
    "GAS", "CVI", "GPP", "SWN", "ROSE", "RRC", "GPOR", "AR", "EIA", "COP",
    "XOM", "CVX", "HAL", "BKR", "EIA", "MRO", "OXY", "SLB", "WMB", "HES",
    "PSX", "DVN", "APA", "CPE", "KMI", "RRC", "PXD", "TTE", "BP", "SHEL",
    "TOT", "BHP", "NBL", "NEM", "NOG", "KOS", "VLO", "CHK", "WLL", "EIA",
    "XOM", "CVX", "RRC", "PXD", "OXY", "MRO", "HAL", "BKR", "EIA", "NBL",
    "APA", "KMI", "SLB", "WMB", "HES", "DVN", "COP", "FTI", "TRP", "ENB",
    "SU", "KMI", "RDS.A", "RDS.B", "TOT", "BP", "E", "PPL", "EIA", "XOM",
    "CVX", "HAL", "PSX", "NBL", "FANG", "EOG", "PXD", "CVE", "CPE", "NOG",
    "WLL", "SD", "MUR", "AR", "GAS", "CVI", "GPP", "ROSE", "RRC", "GPOR",
    "AR", "RIG", "EIA", "HES", "KOG", "EQT", "CVX", "OXY", "RDS.B", "SLB",
    "FTI", "NOG", "BCEI", "CDEV", "SM", "GAS", "KOS", "XOM", "BHI", "MUR",
    "CLR", "MRO", "PSX", "EIA", "NEM", "NBL", "EQT", "HES", "CPE", "PXD",
    "WLL", "OXY", "DVN", "HES", "MUR", "NOG", "CDEV", "CPE", "ROSE", "GPOR",
    "RRC", "KMI", "RIG", "FANG", "CVE", "EIA", "WMB", "ENB", "TRP", "PBR",
    "MUR", "COP", "EIA", "NOG", "KOS", "BCEI", "CLR", "AR", "EIA", "KMI"
]

industrials = [
    "BA", "CAT", "DE", "HON", "LMT", "MMM", "RTX", "UPS", "CSX", "UNP",
    "NSC", "DOV", "EMR", "ITW", "LUV", "GD", "TMO", "CME", "ROK", "AOS",
    "NUE", "PCAR", "DHR", "ZBH", "JCI", "ETN", "MTD", "KSU", "VMC", "XPO",
    "WAB", "RHI", "CMA", "LNC", "TRV", "GE", "PH", "PSX", "NVR", "DHI",
    "LEN", "PHM", "MAS", "APD", "PPG", "AXTA", "SHW", "WAT", "COV", "RTN",
    "TTC", "ALB", "AMT", "GRMN", "HES", "FISV", "RBC", "ORCL", "FIS", "CNC",
    "UNP", "NSC", "GS", "BAC", "JCI", "FLS", "PLD", "SWK", "LII", "BHI",
    "FCX", "JEC", "KBR", "KLAC", "HCA", "PHM", "CMS", "AEE", "VLO", "CME",
    "LMT", "WBA", "XOM", "AIG", "RHI", "X", "CVE", "CHTR", "KMI", "PXD",
    "NUE", "NKE", "GOOGL", "MA", "TSLA", "AAPL", "MSFT", "V", "ADBE",
    "NVDA", "AMD", "QCOM", "INTC", "CSCO", "IBM", "MS", "GS", "CME", "WAB",
    "ALXN", "RHI", "PLD", "CSX", "NEM", "CMA", "BWA", "DOV", "NKE", "HON",
    "ADSK", "KSU", "CBRE", "LMT", "HIG", "TDY", "ECL", "VFC", "MTD", "VZ",
    "HST", "ITW", "IR", "GWW", "NUE", "HPE", "FLS", "HUBB", "MRO", "VMC",
    "TSCO", "AAL", "KEYS", "EL", "RHI", "AFL", "FCX", "HST", "FMC", "APD",
    "CME", "LUV", "MDT", "XOM", "BA", "CME", "DE", "BA", "NEM", "LMT",
    "TMO", "AFL", "HPE", "VZ", "NEM", "LUV", "DOV", "STX", "WAB", "BWA",
    "XYL", "PXD", "FMC", "PWR", "TSLA", "DHR", "HUBB", "KSU", "NTRS", "VLO",
    "MCO", "BWA", "FTI", "NSC", "TMO", "LMT", "ADM", "KBR", "ORCL", "PSX",
    "GPN", "DE", "NKE", "BIDU", "CME", "COG", "JCI", "ORCL", "NEM", "ECL",
    "ACGL", "PXD", "IR", "KMX", "MRO", "BR", "TRMB", "AMT", "STX", "RHI",
    "CHTR", "WBA", "FLS", "LMT", "HST", "GWW", "YUM", "KEY", "PPG", "RHI",
    "HAL", "XOM", "WAT", "FCX", "BWA", "MAA", "LNT", "SPG", "CME", "PPL",
    "MCO", "KBR", "KIM", "CME", "HST", "KEYS", "RHI", "TRMB", "BXP", "UNP"
]

telecommunications = [
    "VZ", "T", "CMCSA", "TMUS", "DISCA", "DISCK", "CTL", "FTR", "CVC", "TDS",
    "LUMN", "CHTR", "SBAC", "AMT", "LBTYA", "LBTYK", "GCI", "TEF", "BT", "T",
    "VZ", "CNSL", "FISV", "TWTR", "FB", "GOOGL", "AMZN", "NFLX", "AAPL", "MSFT",
    "V", "MA", "CSCO", "ERIC", "NOK", "ATVI", "WBD", "TMO", "ZAYO", "MCHP",
    "QCOM", "NTRA", "RNG", "HUM", "XRX", "CDW", "PSTG", "KEYS", "DOCU", "NEWR",
    "DISH", "SPLK", "PLTR", "NDAQ", "LBTYA", "LBTYK", "IPG", "SPOT", "PINS", 
    "RBLX", "BMBL", "FVRR", "GPN", "PLUG", "ENPH", "FICO", "DDOG", "NET", 
    "SNOW", "ZS", "MTCH", "MCHP", "ROKU", "HUBS", "CNSL", "FTNS", "T", 
    "VZ", "UBER", "LYFT", "GOOG", "GOOGL", "MSFT", "AMZN", "AAPL", "NVDA",
    "INTC", "ORCL", "PYPL", "UBS", "DTE", "MNDY", "FTNT", "MSTR", "LUV", 
    "NOK", "SSTK", "QCOM", "PDD", "JBL", "NTAP", "MTCH", "JBL", "EBAY", 
    "FSLY", "TWLO", "BIDU", "RBLX", "FANG", "AVGO", "MRVL", "HPE", "FIS", 
    "MCHP", "CLVS", "FTNT", "CDW", "TWLO", "VEEV", "PINS", "VMW", "CRWD", 
    "OKTA", "EVBG", "RNG", "HUBS", "TEAM", "SQ", "SPGI", "WIX", "NKE",
    "MNDY", "PAYC", "VRSN", "GS", "MS", "LULU", "RH", "MRVL", "AKAM", 
    "NTRA", "WIX", "V", "MA", "SHOP", "PYPL", "SE", "PDD", "MSFT", 
    "AMZN", "GOOGL", "AAPL", "META", "NFLX", "BABA", "JD", "CRM", "NVDA",
    "FIS", "FISV", "GPN", "MA", "V", "DTE", "SPOT", "SPLK", "BMBL", 
    "WIX", "RBLX", "TDY", "ALGN", "DXCM", "XPEL", "QDEL", "BMBL", "NET",
    "DOCU", "TTD", "ENPH", "PLUG", "CHTR", "NDAQ", "CSCO", "AMD", "BA",
    "V", "AMZN", "TSLA", "AAPL", "MSFT", "GOOGL", "META", "NFLX", "CRM",
    "NVDA", "PYPL", "IBM", "INTC", "TXN", "ORCL", "QCOM", "ADBE", "MA", 
    "V", "WMT", "HD", "COST", "NKE", "LOW", "TMO", "DIS", "XOM"
]

materials = [
    "LIN", "PPG", "NEM", "ECL", "APD", "DOW", "SHW", "MON", "IFF", "WLK",
    "NUE", "STLD", "FMX", "WRK", "PFE", "PPLT", "GGB", "IP", "FMC", "MEOH",
    "LMT", "BHP", "RIO", "VALE", "BHP", "PPL", "SABR", "TTM", "OZK", "NTR",
    "HUN", "WTRG", "KRO", "FNV", "MRM", "CC", "X", "NEM", "CENX", "GLW",
    "VMC", "HUN", "AL", "CX", "LMT", "VALE", "AU", "SCCO", "KSU", "JHX",
    "HRS", "LMT", "NUE", "PPLT", "TSE", "AUY", "MSA", "WMB", "NEM", "CMA",
    "PLG", "PSX", "HEES", "FCX", "NUE", "CC", "ECL", "X", "VALE", "LUV",
    "FCX", "SABR", "HUN", "VMC", "STLD", "AL", "BHP", "SHW", "GOLD", "FMC",
    "NEM", "SCCO", "NUE", "HUN", "KRO", "WLK", "LYB", "WTRG", "MPW", "GGB",
    "DOW", "WRK", "ECL", "CC", "APD", "STLD", "GGB", "CENX", "HUN", "OZK",
    "NEM", "PPLT", "VALE", "ZTO", "CENX", "GLW", "GOLD", "SHW", "MUR", "NUE",
    "X", "CC", "FMX", "AU", "MRO", "NTR", "HUN", "VMC", "BHP", "KRO",
    "FMC", "MSA", "HUN", "KSU", "PLG", "WRK", "FF", "LMT", "FCX", "PPL",
    "MPW", "ECL", "AEM", "AUY", "CC", "X", "BHP", "GGB", "NEM", "STLD",
    "WTRG", "AL", "FMX", "WMB", "VALE", "HUN", "SHW", "FMC", "X", "WRK",
    "NUE", "PSX", "FCX", "SABR", "STLD", "KRO", "GLW", "NEM", "NUE", "LMT",
    "CC", "ECL", "PLG", "VALE", "KSU", "HUN", "SABR", "MPW", "SHW", "X",
    "AU", "WMB", "DOW", "VMC", "GGB", "FMX", "MUR", "HUN", "NEM", "AL",
    "KRO", "WTRG", "FCX", "WRK", "GLW", "BHP", "CC", "NUE", "STLD", "PPL",
    "FMC", "LMT", "SABR", "VALE", "PPLT", "HUN", "X", "MSA", "FF", "MPW",
    "WMB", "GOLD", "NEM", "AL", "FMX", "DOW", "CC", "AEM", "FMC", "BHP",
    "KRO", "WRK", "ECL", "NUE", "SHW", "VALE", "LMT", "X", "GGB", "NEM"
]

etfs = [
    "SPY", "IVV", "VOO", "VTI", "XOM", "QQQ", "IWM", "XLB", "XLC", "XLI",
    "XLB", "XLF", "XLY", "XLP", "XPS", "XPR", "XSD", "XSE", "XRT", "XSB",
    "XLB", "XCI", "XCL", "XMB", "XOM", "VUG", "VTV", "VYM", "VBR", "VDE",
    "VFH", "VHT", "VLO", "VPU", "VTV", "VWO", "VYM", "VNQ", "VTI", "VYM",
    "VOO", "VOE", "VONG", "VPL", "VTI", "VZ", "WMT", "XLB", "XLC", "XLI",
    "XLB", "XLF", "XLY", "XLP", "XLB", "XME", "XLC", "XLI", "XLY", "XLP",
    "XLC", "XLP", "XLB", "XLI", "XLY", "XME", "XLB", "XLC", "XLI", "XLY",
    "XLP", "XRT", "XSD", "XTL", "XOP", "XEN", "XLB", "XLI", "XME", "XLP",
    "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI", "XLY",
    "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI",
    "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC",
    "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB",
    "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN",
    "XLB", "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP",
    "XEN", "XLB", "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL",
    "XOP", "XEN", "XLB", "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD",
    "XTL", "XOP", "XEN", "XLB", "XLC", "XLI", "XLY", "XLP", "XRT", "XSB",
    "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI", "XLY", "XLP", "XRT",
    "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI", "XLY", "XLP",
    "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI", "XLY",
    "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC", "XLI",
    "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB", "XLC",
    "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN", "XLB",
    "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP", "XEN",
    "XLB", "XLC", "XLI", "XLY", "XLP", "XRT", "XSB", "XSD", "XTL", "XOP"
]

leveraged_stocks = [
    "SPXL", "SPXS", "TQQQ", "SQQQ", "UPRO", "SDOW", "LABU", "LABD", "FAS", "FAZ",
    "SOXL", "SOXS", "TNA", "TZA", "UDOW", "SRTY", "DFEN", "DUST", "NUGT", "JNUG",
    "JDST", "TECL", "TECS", "CURE", "DRIP", "GUSH", "ERX", "ERY", "MVV", "MZZ",
    "QLD", "QID", "SFLA", "BIB", "BIS", "BOIL", "KOLD", "UGAZ", "DGAZ", "TBT",
    "TMV", "TMF", "UST", "EDC", "EDZ", "EURL", "EUO", "DRN", "DRV", "URE",
    "SRS", "RETL", "REK", "ROM", "REW", "UDOW", "SDOW", "PILL", "SMDD", "MIDU",
    "MIDZ", "LEU", "LEZ", "FNGU", "FNGD", "CWEB", "YINN", "YANG", "CHAU", "CHAD",
    "TQQQ", "SQQQ", "TNA", "TZA", "DRIP", "GUSH", "LABU", "LABD", "TECL", "TECS",
    "DFEN", "DUSL", "UCO", "SCO", "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW",
    "TQQQ", "SQQQ", "FAS", "FAZ", "CURE", "DRN", "DRV", "URE", "SRS", "RETL",
    "REK", "SOXL", "SOXS", "LABU", "LABD", "BIB", "BIS", "DUST", "NUGT", "JNUG",
    "JDST", "GUSH", "DRIP", "ERX", "ERY", "MVV", "MZZ", "UCO", "SCO", "FNGU",
    "FNGD", "KOLD", "BOIL", "UGAZ", "DGAZ", "TBT", "TMV", "TMF", "UST", "EDC",
    "EDZ", "YINN", "YANG", "CWEB", "EUO", "CHAU", "CHAD", "TQQQ", "SQQQ", "TNA",
    "TZA", "DRIP", "GUSH", "LABU", "LABD", "TECL", "TECS", "DFEN", "DUSL", "UCO",
    "SCO", "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW", "FAS", "FAZ", "CURE",
    "DRN", "DRV", "URE", "SRS", "RETL", "REK", "SOXL", "SOXS", "LABU", "LABD",
    "BIB", "BIS", "DUST", "NUGT", "JNUG", "JDST", "GUSH", "DRIP", "ERX", "ERY",
    "MVV", "MZZ", "UCO", "SCO", "FNGU", "FNGD", "KOLD", "BOIL", "UGAZ", "DGAZ",
    "TBT", "TMV", "TMF", "UST", "EDC", "EDZ", "YINN", "YANG", "CWEB", "EUO",
    "CHAU", "CHAD", "SOXL", "SOXS", "SPXL", "SPXS", "TQQQ", "SQQQ", "TNA", "TZA",
    "UDOW", "SDOW", "LABU", "LABD", "DRIP", "GUSH", "TECL", "TECS", "DFEN", "DUSL",
    "ERX", "ERY", "MVV", "MZZ", "UCO", "SCO", "FNGU", "FNGD", "CURE", "CWEB",
    "TQQQ", "SQQQ", "LABU", "LABD", "NUGT", "DUST", "JNUG", "JDST", "SOXL", "SOXS",
    "SPXL", "SPXS", "UDOW", "SDOW", "TNA", "TZA", "TECL", "TECS", "GUSH", "DRIP",
    "CWEB", "YINN", "YANG", "FNGU", "FNGD", "ERX", "ERY", "DFEN", "DUSL", "LABU",
    "LABD", "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW", "TQQQ", "SQQQ", "TNA",
    "TZA", "FAS", "FAZ", "LABU", "LABD", "GUSH", "DRIP", "TECL", "TECS", "DFEN",
    "DUSL", "ERX", "ERY", "MVV", "MZZ", "CWEB", "TQQQ", "SQQQ", "LABU", "LABD",
    "NUGT", "DUST", "JNUG", "JDST", "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW",
    "TNA", "TZA", "TECL", "TECS", "GUSH", "DRIP", "CWEB", "YINN", "YANG", "FNGU",
    "FNGD", "ERX", "ERY", "DFEN", "DUSL", "LABU", "LABD", "SOXL", "SOXS", "SPXL",
    "SPXS", "UDOW", "SDOW", "TQQQ", "SQQQ", "TNA", "TZA", "FAS", "FAZ", "LABU",
    "LABD", "GUSH", "DRIP", "TECL", "TECS", "DFEN", "DUSL", "ERX", "ERY", "MVV",
    "MZZ", "CWEB", "TQQQ", "SQQQ", "LABU", "LABD", "NUGT", "DUST", "JNUG", "JDST",
    "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW", "TNA", "TZA", "TECL", "TECS",
    "GUSH", "DRIP", "CWEB", "YINN", "YANG", "FNGU", "FNGD", "ERX", "ERY", "DFEN",
    "DUSL", "LABU", "LABD", "SOXL", "SOXS", "SPXL", "SPXS", "UDOW", "SDOW", "TQQQ",
    "SQQQ", "TNA", "TZA", "FAS", "FAZ", "LABU", "LABD", "GUSH", "DRIP", "TECL",
    "TECS", "DFEN", "DUSL", "ERX", "ERY", "MVV", "MZZ"
]
#_______________________________________________________________________________________________


@tasks.loop(minutes=10)
async def short_trade_all():

    await delete_and_recreate_channel("random-all")
    
    while True:  # Végtelen ciklus
        symbols = random.sample(technology + healthcare + financials + consumer_discretionary + energy + industrials + telecommunications + materials + etfs + leveraged_stocks, 300)
        guild = discord.utils.get(client.guilds, id=int(ALLOWED_GUILD_ID))
        
        if guild:
            channel = discord.utils.get(guild.text_channels, name='random-all')
            
            if channel:
                for symbol in symbols:
                    link = f'https://api.wsj.net/api/kaavio/charts/big.chart?nosettings=1&symb={symbol}&type=4&time=3&freq=6&style=330&lf=6&lf2=0&lf3=0&size=2&height=335&width=579&mocktick=1&rr=1726150438577'
                    await channel.send(link)
                    await asyncio.sleep(0.4)

        await asyncio.sleep(60 * 8)  # Várj 1 órát, mielőtt újra lefut a ciklus



@tasks.loop(minutes=10)
async def short_trade_leveraged():

    await delete_and_recreate_channel("random-leveraged")
    
    while True:  # Végtelen ciklus
        symbols = random.sample(leveraged_stocks, 300)
        guild = discord.utils.get(client.guilds, id=int(ALLOWED_GUILD_ID))
        
        if guild:
            channel = discord.utils.get(guild.text_channels, name='random-leveraged')
            
            if channel:
                for symbol in symbols:
                    link = f'https://api.wsj.net/api/kaavio/charts/big.chart?nosettings=1&symb={symbol}&type=4&time=3&freq=6&style=330&lf=6&lf2=0&lf3=0&size=2&height=335&width=579&mocktick=1&rr=1726150438577'
                    await channel.send(link)
                    await asyncio.sleep(0.4)

        await asyncio.sleep(60 * 8)  # Várj 1 órát, mielőtt újra lefut a ciklus



async def delete_and_recreate_channel(channel_name):
    guild = discord.utils.get(client.guilds, id=ALLOWED_GUILD_ID)
    if guild:
        # Keressük meg a csatornát név alapján
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel:
            # Csatorna törlése
            await channel.delete()

            # Keresünk egy kategóriát "random" név alapján
            category = discord.utils.get(guild.categories, name="random")
            
            if category:
                # Csatorna újra létrehozása a "random" nevű kategóriában
                await guild.create_text_channel(channel_name, category=category)
            else:
                print("Category 'random' not found.")
            
        else:
            print(f"Channel '{channel_name}' not found.")
    else:
        print("Guild not found.")


#_______________________________________________________________________________________________


# Bot események kezelése
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    if not periodic_update_losers.is_running():
        periodic_update_losers.start()

    if not periodic_update_prices.is_running():
        periodic_update_prices.start()

    if not periodic_update_gainers.is_running():
        periodic_update_gainers.start()
    
    short_trade_all.start()

    short_trade_leveraged.start()


@client.event
async def on_disconnect():
    print(f'{client.user} disconnected. Attempting to reconnect...')


@client.event
async def on_resumed():
    print(f'{client.user} has resumed the session.')


client.run(TOKEN)
