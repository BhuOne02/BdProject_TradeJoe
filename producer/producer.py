import sys
from pathlib import Path

path_to_utils = Path(__file__).parent.parent
sys.path.insert(0, str(path_to_utils))

from confluent_kafka import Producer
from dotenv import load_dotenv
from logs.logger import setup_logger

from producer_utils import retrieve_real_time_data
from script.utils import load_environment_variables
load_dotenv()


# producer.py
kafka_bootstrap_servers = "kafka:9092"  # Use service name and internal port
kafka_config = {    
    "bootstrap.servers": kafka_bootstrap_servers,
}
producer = Producer(kafka_config)

if __name__ == '__main__':
    logger = setup_logger(__name__, 'producer.log')
    logger.info("Testing Kafka")

    test_message = {
        'test': 'This is a test message',
        'timestamp': '2024-12-09T22:00:00Z'
    }

    try:
        logger.info("Producer inside")
        # Produce the message
        producer.produce(
            topic=real-time-stock-prices,
            key='test-key',
            value=json.dumps(test_message),
            callback=delivery_report
        )
        # Wait for all messages to be delivered
        producer.flush()
    except Exception as e:
        print(f"An error occurred while producing message: {e}")





    # try:
    #     env_vars = load_environment_variables()
    #     producer.produce(real-time-stock-prices, key=key, partition=partition, value=json.dumps(message).encode("utf-8"))
    #     # retrieve_real_time_data(
    #     #     producer,
    #     #     env_vars.get("STOCKS"),
    #     #     ,
    #     #     logger
    #     # )

    # except Exception as e:
    #     logger.error(f"An error occurred: {e}")


