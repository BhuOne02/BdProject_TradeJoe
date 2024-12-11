import sys
from pathlib import Path
import json

path_to_utils = Path(__file__).parent.parent
sys.path.insert(0, str(path_to_utils))

from confluent_kafka import Producer
from dotenv import load_dotenv
from logs.logger import setup_logger

from producer_utils import retrieve_real_time_data
from script.utils import load_environment_variables
load_dotenv()


# producer.py
kafka_bootstrap_servers = "kafka:9092"
kafka_config = {
    "bootstrap.servers": kafka_bootstrap_servers,
}
producer = Producer(kafka_config)



if __name__ == '__main__':
    logger = setup_logger(__name__,'producer.log')
    logger.info("Actual Code")

    try:
        env_vars = load_environment_variables()
        retrieve_real_time_data(
            producer,
            env_vars.get("STOCKS"),
            'real-time-stock-prices',
            logger
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")


