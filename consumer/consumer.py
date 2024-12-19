import sys
# append the path of the parent directory
sys.path.append("/app")


from pyspark.sql import SparkSession, Row
from pyspark.sql.window import Window
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
from datetime import datetime, timedelta
import os
import json
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from datetime import datetime

from confluent_kafka import Consumer, KafkaException, KafkaError

conf = {
    'bootstrap.servers': 'kafka:9092',  # Replace with your Kafka broker address
    'auto.offset.reset': 'earliest',  # Start reading at the earliest message
    'group.id': 'stock-price-consumer-group',  # Consumer group ID
}

# Create Consumer Instance
consumer = Consumer(conf)

# Subscribe to the topic
KAFKA_TOPIC_NAME = "real-time-stock-prices"
consumer.subscribe([KAFKA_TOPIC_NAME])
print(f"Subscribed to Kafka topic: {KAFKA_TOPIC_NAME}")

from logs.logger import setup_logger
from InfluxDBWriter import InfluxDBWriter
import findspark
findspark.init()


# Related to kafka
KAFKA_TOPIC_NAME = "real-time-stock-prices"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
postgresql_properties  = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

stock_price_schema = StructType([
    StructField("stock", StringType(), True),
    StructField("date", TimestampType(), True),
    StructField("open", DoubleType(), True),
    StructField("high", DoubleType(), True),
    StructField("low", DoubleType(), True),
    StructField("close", DoubleType(), True),
    StructField("volume", DoubleType(), True)
])

scala_version = '2.12'
spark_version = '3.4.4'
packages = [
    f'org.apache.spark:spark-sql-kafka-0-10_{scala_version}:{spark_version}',
    'org.apache.kafka:kafka-clients:2.8.1'
]

if __name__ == "__main__":
    print("New DB")
    # Fetch environment variables
    influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "stock_data_bucket")  # Default to stock_data_bucket
    influxdb_measurement = os.getenv("INFLUXDB_MEASUREMENT", "stock-price-v1")  # Default to stock-price-v1
    influxdb_org = os.getenv("INFLUX_ORG", "primary")  # Default to primary
    influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")  # Update with your InfluxDB host URL
    influxdb_token = os.getenv("INFLUX_TOKEN")  # Replace with your actual token
    # Initialize client
    influxdb_writer = InfluxDBClient(
    url=influxdb_url,
    token=influxdb_token,
    org=influxdb_org
    ).write_api()


    logger = setup_logger(__name__, 'consumer.log')
    logger.info("Testing consumer")
    spark = (
        SparkSession.builder.appName("KafkaInfluxDBStreaming")
        .master("spark://spark-master:7077")
        .config("spark.jars.packages", ",".join(packages))
        .config("spark.executor.extraClassPath", "/app/packages/postgresql-42.2.18.jar")
        .getOrCreate()
    )

    # List to Store Messages
    messages = []

    try:
        while True:
            # Poll for new messages
            msg = consumer.poll(timeout=1.0)
            print("msg",msg)

            if msg is None:
                continue  # No message, continue polling
            if msg.error():
                # Handle any Kafka errors
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    print(f"End of partition reached {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                # Successfully received message
                value = msg.value().decode('utf-8')
                print(f"Received message: {value}")
                try:
                    # Parse the JSON and convert date string to datetime
                    data = json.loads(value)
                    if "date" in data and data["date"]:
                        data["date"] = datetime.fromisoformat(data["date"])  # Convert ISO 8601 string to datetime
                    messages.append(data)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Failed to parse message: {e}")
                
            # Create a Spark DataFrame from messages
            if messages:
                rows = [Row(
                        stock=msg["stock"],
                        date=msg["date"],
                        open=float(msg["open"]) if msg["open"] is not None else None,
                        high=float(msg["high"]) if msg["high"] is not None else None,
                        low=float(msg["low"]) if msg["low"] is not None else None,
                        close=float(msg["close"]) if msg["close"] is not None else None,
                        volume=float(msg["volume"]) if msg["volume"] is not None else None,
                    )
                    for msg in messages
                    ]
                messages.clear()  # Clear messages after processing
                df = spark.createDataFrame(rows, schema=stock_price_schema)
                
                # Show DataFrame
                df.show()

                # Write each row to InfluxDB
                # influxdb_writer = InfluxDBWriter('stock-data-bucket', 'stock-price-v1')
                for row in df.collect():
                    # Extract fields for InfluxDB
                    timestamp = row["date"]  # Assuming 'date' is the timestamp field
                    print("timestamp",timestamp)
                    tags = {"stock": row["stock"]}
                    print("tag",tags)
                    fields = {
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"]
                    }
                    print("tag",fields)
                        # Create a point for InfluxDB
                    point = Point(influxdb_measurement) \
                        .tag("stock", tags["stock"]) \
                        .field("open", fields["open"]) \
                        .field("high", fields["high"]) \
                        .field("low", fields["low"]) \
                        .field("close", fields["close"]) \
                        .field("volume", fields["volume"]) \
                        .time(timestamp)
                    
                    # Write test data to InfluxDB
                    try:
                        influxdb_writer.write(bucket=influxdb_bucket, record=point)
                        print("Real time data written successfully!")
                    except Exception as e:
                        print(f"Failed to write test data: {e}")

    except KeyboardInterrupt:
        print("Exiting Kafka consumer...")

    finally:
        # Close the consumer to release resources
        consumer.close()




   