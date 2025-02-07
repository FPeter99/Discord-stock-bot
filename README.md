# Discord Stock Bot

This Discord bot can handle this server: [Discord Server](https://discord.gg/HX8AmCcy9z)  
The server contains multiple rooms where the bot posts current stock prices and charts.

<p align="center">
  <img src="https://user-images.githubusercontent.com/74038190/212284115-f47cd8ff-2ffb-4b04-b5bf-4d1c14c0247f.gif" width="1100" />
</p>

## How to Start It

1. Create rooms named after stock symbols like "AAPL" or "SPY". It works with almost any kind of stock or ETF.
2. Create two rooms named "top-stock-losers" and "top-stock-gainers". The bot will update these rooms with the daily top loser and gainer stocks. (Note: It doesn't work perfectly because the API doesn't always provide the biggest losers and gainers.)
3. Create two rooms named "random-leveraged" and "random-all". In these rooms, the bot will post hundreds of charts from the biggest companies across every market, with a three-day interval, to help find short trades faster.
4. Create a `.env` file next to `main.py` (make sure the Python file can access the `.env`) and paste the content from "Convert_this_to_.env.txt". Fill in the `.env` file with the required data, replacing the commented text with your API keys. You can get a free API key here: [Twelve Data](https://twelvedata.com/).

## How It Works

The bot handles three types of rooms:
- **Normal stock and ETF rooms**
- **Top gainers/losers rooms**
- **Random all/leveraged rooms**

### Stock and ETF Rooms:
- The bot updates these rooms every 5 minutes. It first deletes the last 7 messages it sent (not your messages). Then, it sends an embed with:
  - Current price
  - 1-day, 1-month, and 1-year prices
  - Percentage changes for each
- The bot will also send a weekly, daily, and 3-day candlestick chart.

### Top Stock Losers and Gainers:
- These rooms update every 30 minutes. After deleting the last 7 messages, the bot sends a link with data on the top loser and gainer stocks.
- An embed with the top 10 losers and gainers will also be sent, though it may not always be very accurate.

### Random Leveraged and Random All:
- In these rooms, the bot will send 300 charts from the database. This includes:
  - 400 leveraged stocks
  - Around 2000 of the biggest stocks from sectors like technology, healthcare, etc.

## Project History

I started working on this project in the summer of 2024 (when I was 15). My goal is that when I turn 18, I want to make the best investment and financial decisions possible.
