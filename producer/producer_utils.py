import sys
# append the path of the parent directory
sys.path.append("./")

import yfinance as yf
import pandas as pd
import numpy as np

import json
from datetime import datetime, timedelta, time, timezone
from dotenv import load_dotenv
import time as t

load_dotenv()

def send_to_kafka(producer, topic, key, partition, message):
    # print("sent to kafka", message)
    producer.produce(topic, key=key, value=json.dumps(message).encode("utf-8"))
    producer.flush()

def retrieve_historical_data(producer, stock_symbol, kafka_topic, logger):
    logger.info("Starting to retrieve historical data")
    stock_symbols = stock_symbol.split(",") if stock_symbol else []
    if not stock_symbols:
        logger.error("No stock symbols provided in the environment variable.")
        exit(1)

    for symbol_index, stock_symbol in enumerate(stock_symbols):
        try:
            stock_symbol = stock_symbol.strip()
            start_date = '2023-12-10'
            end_date = '2024-12-11'
            logger.info(start_date)
            logger.info(end_date)

            historical_data = yf.download(
                tickers=stock_symbol,
                start=start_date,
                end=end_date,
                prepost=True,
                progress=False
            )

            # Check if data is retrieved
            if historical_data.empty:
                logger.info(f"No data fetched for stock symbol {stock_symbol} between {start_date} and {end_date}.")
                continue

            logger.info(f"Data fetched successfully for stock symbol {stock_symbol}: {historical_data.head()}")

            # Reset index to avoid indexing errors
            historical_data.reset_index(inplace=True)

            # Handle prefixed column names
            if stock_symbol in historical_data.columns[0]:
                historical_data.columns = [col.split('_', 1)[-1] if '_' in col else col for col in historical_data.columns]
   
            # Iterate through rows and send to Kafka
            for index, row in historical_data.iterrows():
                logger.info("row:")
                logger.info(row[0])
                date_str = row[0].strftime('%Y-%m-%d')
                try:
                    historical_data_point = {
                        'stock': stock_symbol,
                        'date': date_str,
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }

                    if all(value is not None for value in historical_data_point.values()):
                        send_to_kafka(producer, kafka_topic, stock_symbol, symbol_index, historical_data_point)
                        logger.info(f"Stock value retrieved and pushed to Kafka topic {kafka_topic}")

                    logger.info(f"Sent data point for {stock_symbol} at {row['Date']}")
                except Exception as row_error:
                    logger.error(f"Error processing row for {stock_symbol}: {row_error}")
        except Exception as e:
            logger.error(f"Error fetching data for {stock_symbol}: {e}")


def retrieve_real_time_data(producer, stock_symbol, kafka_topic, logger):
    logger.info("retrieve_real_time_data")

    # Define the stock symbol for real-time data
    retrieve_historical_data(producer, stock_symbol, kafka_topic, logger)
    stock_symbols = stock_symbol.split(",") if stock_symbol else []
    if not stock_symbols:
        logger.error(f"No stock symbols provided in the environment variable.")
        exit(1)
    while True:
        # Fetch real-time data for the last 1 minute
        current_time = datetime.now()
        is_market_open_bool = is_stock_market_open(current_time)
        if is_market_open_bool:
            end_time = datetime.now() 
            start_time = end_time - timedelta(days= 1)
            for symbol_index, stock_symbol in enumerate(stock_symbols):
                real_time_data = yf.download(stock_symbol, start=start_time, end=end_time, interval="2m")
                print(real_time_data)
                if not real_time_data.empty:
                    # Convert and send the latest real-time data point to Kafka
                    latest_data_point = real_time_data.iloc[-1]
                    real_time_data_point = {
                        'stock': stock_symbol,
                        'date': latest_data_point.name.strftime('%Y-%m-%d %H:%M:%S'),
                        'open': float(latest_data_point['Open']),
                        'high': float(latest_data_point['High']),
                        'low': float(latest_data_point['Low']),
                        'close': float(latest_data_point['Close']),
                        'volume': float(latest_data_point['Volume'])
                    }
                    json.dumps(real_time_data_point) 
                    send_to_kafka(producer, kafka_topic, stock_symbol, symbol_index, real_time_data_point)
                    logger.info(f"Stock value retrieved and pushed to kafka topic {kafka_topic}")
        else:
            for symbol_index, stock_symbol in enumerate(stock_symbols):
                null_data_point = {
                    'stock': stock_symbol,
                    'date': current_time.isoformat(),
                    'open': None,
                    'high': None,
                    'low': None,
                    'close': None,
                    'volume': None
                }
                send_to_kafka(producer, kafka_topic, stock_symbol, symbol_index, null_data_point)
        t.sleep(3) 

def get_stock_details(stock_symbol, logger):
    stock_symbols = stock_symbol.split(",") if stock_symbol else []
    print(stock_symbols)
    logger.info(stock_symbols)
    if not stock_symbols:
        logger.error(f"No stock symbols provided in the environment variable.")
        exit(1)
    # Create a Ticker object for the specified stock symbol
    stock_details = []
    for stock_symbol in stock_symbols:
        try:
        # Create a Ticker object for the specified stock symbol
            ticker = yf.Ticker(stock_symbol)

            # Retrieve general stock information
            stock_info = {
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Symbol': stock_symbol,
                'ShortName': ticker.info['shortName'],
                'LongName': ticker.info['longName'],
                'Industry': ticker.info['industry'],
                'Sector': ticker.info['sector'],
                'MarketCap': ticker.info['marketCap'],
                'ForwardPE': ticker.info['forwardPE'],
                'TrailingPE': ticker.info['trailingPE'],
                'Currency': ticker.info['currency'],
                'FiftyTwoWeekHigh': ticker.info['fiftyTwoWeekHigh'],
                'FiftyTwoWeekLow': ticker.info['fiftyTwoWeekLow'],
                'FiftyDayAverage': ticker.info['fiftyDayAverage'],
                'Exchange': ticker.info['exchange'],
                'ShortRatio': ticker.info['shortRatio']
            }
            stock_details.append(stock_info)
        except Exception as e:
            logger.info(f"Error fetching stock details for {stock_symbol}: {str(e)}")

    return stock_details

def is_stock_market_open(current_datetime=None):
    # If no datetime is provided, use the current datetime
    if current_datetime is None:
        current_datetime = datetime.now()

    # Define NYSE trading hours in Eastern Time Zone
    market_open_time = time(9, 30)
    market_close_time = time(16, 0)

    # Convert current_datetime to Eastern Time Zone
    current_time_et = current_datetime.astimezone(timezone(timedelta(hours=-4)))

    # Check if it's a weekday and within trading hours
    if current_time_et.weekday() < 5 and market_open_time <= current_time_et.time() < market_close_time:
        return True
    else:
        return False


